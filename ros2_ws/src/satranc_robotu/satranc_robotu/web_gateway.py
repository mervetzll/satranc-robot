"""Same-origin HTTP/WebSocket adapter. Only legal human moves may be submitted.

No arbitrary ROS topic publication, file access or shell commands are exposed.
Default bind is loopback; use an authenticated HTTPS reverse proxy for remote access.
"""
import asyncio
import json
import math
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit

from aiohttp import web, WSMsgType
import chess
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import String

from .web_protocol import CommandGate


class WebGateway(Node):
    def __init__(self):
        super().__init__('web_gateway')
        for key, value in [('host', '127.0.0.1'), ('port', 8080), ('web_root', ''),
                           ('allowed_origin', '')]:
            self.declare_parameter(key, value)
        self.access_key = os.environ.get('SATRANC_CONTROL_KEY', '')
        self.reset_file = os.environ.get('SATRANC_RESET_FILE', '')
        self.reset_session = None
        self.gate = CommandGate()
        self.joints = {}
        self.web_clients = set()
        self.move_pub = self.create_publisher(String, '/human_move', 10)
        self.create_subscription(String, '/robot_state', self.on_state,
                                 QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(JointState, '/joint_states', self.on_joints,
                                 QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))

    def on_state(self, msg):
        try:
            state = json.loads(msg.data)
            chess.Board(state['fen'])
            if state.get('style') not in ('alu', 'pink') or not state.get('session'):
                return
            self.gate.observe(state)
            if self.reset_session and state['session'] != self.reset_session:
                self.reset_session = None
        except (ValueError, KeyError, TypeError, IndexError):
            self.get_logger().warn('Geçersiz robot_state mesajı')

    def on_joints(self, msg):
        joints = dict(zip(msg.name, msg.position))
        required = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5',
                    'finger_left_joint', 'finger_right_joint']
        if all(k in joints and math.isfinite(joints[k]) for k in required):
            self.joints = {k: joints[k] for k in required}
            self.gate.joints_at = self.gate.clock()

    def snapshot(self):
        subscribers = self.move_pub.get_subscription_count()
        reason = 'Başlangıç durumuna dönülüyor; yeni ROS oturumu bekleniyor' if self.reset_session else self.gate.reason(subscribers)
        return {'type': 'state', 'robot': self.gate.state, 'joints': self.joints,
                'can_move': reason is None, 'reason': reason,
                'telemetry_fresh': self.gate.clock() - self.gate.joints_at <= 3,
                'state_fresh': self.gate.clock() - self.gate.state_at <= 3}

    def submit(self, data):
        if isinstance(data, dict) and data.get('type') == 'reset':
            if not self.reset_file or not self.gate.state:
                raise ValueError('Bu sunucu sunum yöneticisiyle başlatılmamış; sıfırlama kullanılamıyor')
            if not self.reset_session:
                self.reset_session = self.gate.state['session']
                Path(self.reset_file).write_text(str(time.time_ns()), encoding='ascii')
            return {'type': 'resetting'}
        if self.reset_session:
            raise ValueError('Başlangıca dönüş sürüyor')
        if not isinstance(data, dict) or data.get('type') != 'move':
            raise ValueError('Yalnızca move komutu destekleniyor')
        uci = data.get('uci')
        if not isinstance(uci, str) or len(uci) > 5:
            raise ValueError('Hamleyi e2e4 biçiminde yazın')
        uci = uci.strip().lower()
        reason = self.gate.reason(self.move_pub.get_subscription_count())
        if reason:
            raise ValueError(reason)
        board = chess.Board(self.gate.state['fen'])
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            raise ValueError('Kurala aykırı hamle')
        self.gate.reserve(uci, self.move_pub.get_subscription_count())
        self.move_pub.publish(String(data=uci))
        return {'type': 'accepted', 'uci': uci}

    async def socket(self, request):
        # Require same-origin or one explicitly configured origin (no wildcard).
        origin = request.headers.get('Origin')
        permitted = self.get_parameter('allowed_origin').value
        if origin:
            same = urlsplit(origin).netloc == request.host and urlsplit(origin).scheme in ('http', 'https')
            if not same and origin != permitted:
                raise web.HTTPForbidden(text='Origin izinli değil')
        else:
            raise web.HTTPForbidden(text='Origin gerekli')
        ws = web.WebSocketResponse(heartbeat=15, max_msg_size=2048)
        await ws.prepare(request)
        if self.access_key:
            try:
                auth = await asyncio.wait_for(ws.receive_json(), timeout=8)
                if not isinstance(auth, dict) or auth.get('type') != 'auth' or not secrets.compare_digest(str(auth.get('key', '')), self.access_key):
                    await ws.close(code=1008, message=b'Access key required')
                    return ws
            except (ValueError, TypeError, asyncio.TimeoutError):
                await ws.close(code=1008, message=b'Authentication timeout')
                return ws
        self.web_clients.add(ws)
        await ws.send_json(self.snapshot())
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        await ws.send_json(self.submit(json.loads(msg.data)))
                    except (ValueError, TypeError, KeyError) as exc:
                        await ws.send_json({'type': 'error', 'message': str(exc)})
        finally:
            self.web_clients.discard(ws)
        return ws

    async def serve_file(self, request):
        name = request.match_info.get('name', 'index.html')
        if name not in ('index.html', 'ros-client.js'):
            raise web.HTTPNotFound()
        root = Path(self.get_parameter('web_root').value)
        if not root.is_absolute() or not (root / name).is_file():
            raise web.HTTPNotFound(text='web_root mutlak web klasörünü göstermeli')
        return web.FileResponse(root / name, headers={'Cache-Control': 'no-store'})

    async def pump(self):
        ticks = 0
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0)
            ticks += 1
            if ticks % 5 == 0:
                packet = self.snapshot()
                for ws in list(self.web_clients):
                    try:
                        await asyncio.wait_for(ws.send_json(packet), timeout=0.3)
                    except (ConnectionError, RuntimeError, asyncio.TimeoutError):
                        self.web_clients.discard(ws)
                        await ws.close()
            await asyncio.sleep(0.01)

    async def run(self):
        app = web.Application()
        app.router.add_get('/ws', self.socket)
        app.router.add_get('/', self.serve_file)
        app.router.add_get('/{name}', self.serve_file)
        runner = web.AppRunner(app)
        await runner.setup()
        try:
            await web.TCPSite(runner, self.get_parameter('host').value,
                             self.get_parameter('port').value).start()
            self.get_logger().info('Web arayüzü hazır: http://127.0.0.1:8080')
            await self.pump()
        finally:
            for ws in list(self.web_clients):
                await ws.close(code=1001, message=b'Server shutdown')
            await runner.cleanup()


def main():
    rclpy.init()
    node = WebGateway()
    try:
        asyncio.run(node.run())
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
