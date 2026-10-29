"""Hamle yürütücü düğümü.

'/chess_move' konusundan gelen UCI hamlesini (örn. "e2e4", "e7e8q") alır, taşı al-bırak
hareketlerine çevirir, her ara noktayı ters kinematikle eklem açılarına dönüştürür ve
kol/tutucu denetleyicilerine yörünge olarak gönderir. Yeme, rok, geçerken alma ve terfiyi
bilir; yenen taşları ve yedek vezirleri tahtanın yanındaki bölmelerde tutar.

'/human_move' konusu da dinlenir: execute_human_moves=True ise (simülasyon) robot insanın
hamlesini de oynar, False ise (gerçek tahta) yalnızca kendi tahta durumunu günceller.
"""
import json
import math
import time
import queue
import threading

import chess
import rclpy
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectoryPoint

from .geometry import Geometry

ARM_JOINTS = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5']
GRIP_JOINTS = ['finger_left_joint', 'finger_right_joint']


def _duration(t):
    return Duration(sec=int(t), nanosec=int((t - int(t)) * 1e9))


class MoveExecutor(Node):
    def __init__(self):
        super().__init__('move_executor')
        g = Geometry()
        for name, default in vars(Geometry()).items():
            self.declare_parameter(name, default)
            setattr(g, name, self.get_parameter(name).value)
        self.g = g
        self.declare_parameter('style', 'alu')
        self.declare_parameter('speed', 0.10)              # parmak ucu hızı, m/s
        self.declare_parameter('points_per_segment', 12)   # bir hareketteki ara nokta sayısı
        self.declare_parameter('execute_human_moves', True)
        # Gazebo gerçek zamandan yavaş çalışabilir (WSL'de yaklaşık 7 kat): bekleme süresi bu katla uzatılır
        self.declare_parameter('timeout_scale', 20.0)
        self.speed = self.get_parameter('speed').value
        self.n_pts = self.get_parameter('points_per_segment').value
        self.exec_human = self.get_parameter('execute_human_moves').value
        self.timeout_scale = self.get_parameter('timeout_scale').value

        self.arm = ActionClient(self, FollowJointTrajectory, '/arm_controller/follow_joint_trajectory')
        self.grip = ActionClient(self, FollowJointTrajectory, '/gripper_controller/follow_joint_trajectory')
        self.status_pub = self.create_publisher(String, '/robot_status', 10)
        self.events_pub = self.create_publisher(String, '/robot_state', QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.done_pub = self.create_publisher(String, '/move_done', 10)
        self.create_subscription(String, '/chess_move', lambda m: self.on_move(m.data, execute=True), 10)
        self.create_subscription(String, '/human_move', lambda m: self.on_move(m.data, execute=self.exec_human), 10)

        self.board = chess.Board()
        n = g.zone_slots
        self.zone = {'w': ['Q'] + [None] * (n - 1), 'b': ['Q'] + [None] * (n - 1)}  # 0. göz: yedek vezir
        self.tip = g.home_xyz()
        self.last_j = None
        self.jobs = queue.Queue()
        self.confirmed_board = chess.Board()
        self.report_lock = threading.RLock()
        self.report = {'ready': False, 'busy': True, 'error': None, 'uci': None,
                       'session': str(time.time_ns()), 'style': self.get_parameter('style').value,
                       'fen': self.confirmed_board.fen(), 'zone': self.zone,
                       'geometry': vars(g)}
        self.publish_state()
        # Monitoring must continue even when simulation time is paused or absent.
        self.status_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.5, self.publish_state, clock=self.status_clock)
        threading.Thread(target=self.worker, daemon=True).start()

    def publish_state(self):
        with self.report_lock:
            self.events_pub.publish(String(data=json.dumps(self.report)))

    def report_state(self, **changes):
        with self.report_lock:
            self.report.update(changes)
            self.publish_state()

    # ---------- planlama ----------
    def say(self, text, level='info'):
        # rclpy aynı satırdan farklı önem düzeyiyle yazmaya izin vermez: her düzeyin kendi çağrısı var
        log = self.get_logger()
        if level == 'error':
            log.error(text)
        else:
            log.info(text)
        self.status_pub.publish(String(data=text))

    def free_slot(self, zone, side):
        for i in range(1, len(zone[side])):
            if zone[side][i] is None:
                return i
        return None

    def on_move(self, uci, execute):
        if self.report['error']:
            self.say('Hata sonrası yeniden başlatma gerekli', 'error')
            return
        try:
            move = chess.Move.from_uci(uci.strip())
        except ValueError:
            self.say(f'Hamle okunamadı: {uci}', 'error')
            return
        if move not in self.board.legal_moves:
            self.say(f'Kurala aykırı hamle: {uci}', 'error')
            return
        if not execute:
            self.board.push(move)
            self.confirmed_board.push(move)
            self.report_state(fen=self.confirmed_board.fen())
            self.done_pub.publish(String(data=uci.strip()))
            self.say(f'{uci} tahtada yapıldı (robot dokunmadı)')
            return
        plan = self.plan(move)
        if plan is None:
            return
        transfers, new_zone = plan
        self.board.push(move)
        self.zone = new_zone
        self.report_state(busy=True)
        self.jobs.put((uci.strip(), transfers, new_zone))

    def plan(self, move):
        """Hamleyi (taş türü, nereden, nereye) taşıma listesine çevirir. Durumu değiştirmez."""
        b = self.board
        zone = {k: list(v) for k, v in self.zone.items()}
        mover = b.piece_at(move.from_square)
        color = 'w' if mover.color == chess.WHITE else 'b'
        frm, to = chess.square_name(move.from_square), chess.square_name(move.to_square)
        out = []
        if b.is_en_passant(move):
            cap_sq = chess.square(chess.square_file(move.to_square), chess.square_rank(move.from_square))
        elif b.is_capture(move):
            cap_sq = move.to_square
        else:
            cap_sq = None
        if cap_sq is not None:
            cap = b.piece_at(cap_sq)
            side = 'w' if cap.color == chess.WHITE else 'b'
            i = self.free_slot(zone, side)
            if i is None:
                self.say('Bölme dolu, yenen taşa yer yok', 'error')
                self.report_state(error='Bölme dolu, yenen taşa yer yok', ready=False, busy=False)
                return None
            zone[side][i] = cap.symbol().upper()
            out.append((cap.symbol().upper(), ('sq', chess.square_name(cap_sq)), ('zone', side, i)))
        if move.promotion:
            pt = chess.piece_symbol(move.promotion).upper()
            j = next((k for k, v in enumerate(zone[color]) if v == pt), None)
            if j is None:
                self.say(f'Bölmede yedek {pt} yok', 'error')
                self.report_state(error=f'Bölmede yedek {pt} yok', ready=False, busy=False)
                return None
            zone[color][j] = None
            i = self.free_slot(zone, color)
            if i is None:
                self.say('Bölme dolu, piyona yer yok', 'error')
                self.report_state(error='Bölme dolu, piyona yer yok', ready=False, busy=False)
                return None
            zone[color][i] = 'P'
            out.append(('P', ('sq', frm), ('zone', color, i)))
            out.append((pt, ('zone', color, j), ('sq', to)))
        else:
            out.append((mover.symbol().upper(), ('sq', frm), ('sq', to)))
            if b.is_castling(move):
                rank = frm[1]
                kingside = chess.square_file(move.to_square) == 6
                out.append(('R', ('sq', ('h' if kingside else 'a') + rank), ('sq', ('f' if kingside else 'd') + rank)))
        return out, zone

    def xy(self, loc):
        return self.g.square_xy(loc[1]) if loc[0] == 'sq' else self.g.zone_xy(loc[1], loc[2])

    # ---------- yürütme ----------
    def worker(self):
        self.arm.wait_for_server()
        self.grip.wait_for_server()
        self.say('Denetleyiciler hazır, eve gidiliyor')
        if not self.move_to(self.g.home_xyz(), 'cyl'):
            self.report_state(error='Başlangıç konumuna gidilemedi', ready=False)
            return
        self.report_state(ready=True, busy=not self.jobs.empty())
        while rclpy.ok():
            uci, transfers, new_zone = self.jobs.get()
            self.report_state(busy=True, uci=uci)
            ok = True
            for t, a, b in transfers:
                if not self.pick_place(t, a, b):
                    ok = False
                    break
            if ok:
                ok = self.move_to(self.g.home_xyz(), 'cyl')
            if not ok:
                self.say(f'{uci} sırasında hata oldu; yeniden başlatma gerekli', 'error')
                self.report_state(error=f'{uci}: hareket başarısız', ready=False, busy=False)
                return
            self.confirmed_board.push_uci(uci)
            self.report_state(fen=self.confirmed_board.fen(), zone=new_zone,
                              busy=not self.jobs.empty(), uci=uci)
            self.done_pub.publish(String(data=uci))
            self.say(f'{uci} tamamlandı')

    def pick_place(self, t, a, b):
        g = self.g
        (ax, ay), (bx, by) = self.xy(a), self.xy(b)
        tz, gz = g.travel_z(), g.grasp_z(t)
        open_w = g.grasp_d(t) / 2 + 0.0035   # her yanda 3,5 mm açılma payı
        close_w = g.grasp_d(t) / 2 - 0.0025  # 2,5 mm sıkıştır: konum denetiminde kavrama kuvveti
        self.say(f'{t}: {a[1] if a[0] == "sq" else "bölme"} → {b[1] if b[0] == "sq" else "bölme"}')
        steps = [
            lambda: self.move_to((ax, ay, tz), 'cyl'),
            lambda: self.gripper(open_w),
            lambda: self.move_to((ax, ay, gz), 'lin'),
            lambda: self.gripper(close_w),
            lambda: self.move_to((ax, ay, tz), 'lin'),
            lambda: self.move_to((bx, by, tz), 'cyl'),
            lambda: self.move_to((bx, by, gz), 'lin'),
            lambda: self.gripper(open_w),
            lambda: self.move_to((bx, by, tz), 'lin'),
        ]
        return all(step() for step in steps)

    def interpolate(self, p0, p1, mode):
        bx, by = self.g.base_xy()
        pts = []
        if mode == 'cyl':  # taban etrafında yay: kol tabanın üstünden geçmez
            a0 = math.atan2(p0[0] - bx, -(p0[1] - by))
            a1 = math.atan2(p1[0] - bx, -(p1[1] - by))
            r0, r1 = math.hypot(p0[0] - bx, p0[1] - by), math.hypot(p1[0] - bx, p1[1] - by)
            da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            for i in range(1, self.n_pts + 1):
                k = i / self.n_pts
                a, r = a0 + da * k, r0 + (r1 - r0) * k
                pts.append((bx + math.sin(a) * r, by - math.cos(a) * r, p0[2] + (p1[2] - p0[2]) * k))
        else:  # düz çizgi: dikey iniş ve çıkış
            for i in range(1, self.n_pts + 1):
                k = i / self.n_pts
                pts.append(tuple(p0[c] + (p1[c] - p0[c]) * k for c in range(3)))
        return pts

    def move_to(self, target, mode):
        pts = self.interpolate(self.tip, target, mode)
        sols = []
        prev = self.last_j
        for p in pts:
            j = self.g.ik(*p)
            if j is None:
                self.say(f'Ulaşılamayan nokta: x={p[0]:.3f} y={p[1]:.3f} z={p[2]:.3f}', 'error')
                return False
            j = list(j)
            if prev is not None:  # J5 çene açısını 90°'lik katlarla bir önceki noktaya en yakın tut
                cands = [j[4] + k * math.pi / 2 for k in (-1, 0, 1)]
                cands = [c for c in cands if -math.pi / 2 <= c <= math.pi / 2]
                j[4] = min(cands, key=lambda c: abs(c - prev[4]))
            sols.append(j)
            prev = j
        dist = math.dist(self.tip, target)
        total = max(0.4, dist / self.speed)
        ok = self.send(self.arm, ARM_JOINTS, sols, total)
        if ok:
            self.tip, self.last_j = target, sols[-1]
        return ok

    def gripper(self, half_width):
        return self.send(self.grip, GRIP_JOINTS, [[half_width, half_width]], 0.6)

    def send(self, client, names, positions, total):
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = names
        for i, pos in enumerate(positions):
            pt = JointTrajectoryPoint()
            pt.positions = [float(v) for v in pos]
            pt.time_from_start = _duration(total * (i + 1) / len(positions))
            goal.trajectory.points.append(pt)
        done, result = threading.Event(), {'ok': False, 'expired': False, 'handle': None}

        def on_result(fut):
            try:
                res = fut.result().result
            except Exception:
                done.set()
                return
            result['ok'] = res.error_code == FollowJointTrajectory.Result.SUCCESSFUL
            done.set()

        def on_goal(fut):
            try:
                handle = fut.result()
            except Exception:
                done.set()
                return
            result['handle'] = handle
            if result['expired'] and handle.accepted:
                handle.cancel_goal_async()
                done.set()
                return
            if not handle.accepted:
                done.set()
                return
            handle.get_result_async().add_done_callback(on_result)

        client.send_goal_async(goal).add_done_callback(on_goal)
        if not done.wait(timeout=total * self.timeout_scale + 30.0):
            result['expired'] = True
            if result['handle'] is not None:
                result['handle'].cancel_goal_async()
            self.say('Denetleyici zamanında cevap vermedi', 'error')
            return False
        return result['ok']


def main():
    rclpy.init()
    node = MoveExecutor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
