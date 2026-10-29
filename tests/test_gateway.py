import sys,types,unittest,asyncio
from pathlib import Path
from unittest.mock import Mock
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ros2_ws/src/satranc_robotu'))
import chess
# ROS is not installed on Windows. These adapters test logic, never claim a ROS run.
class Param:
 def __init__(self,value):self.value=value
class Pub:
 def __init__(self):self.messages=[]
 def publish(self,msg):self.messages.append(msg.data)
 def get_subscription_count(self):return 2
class FakeNode:
 @property
 def clients(self):return iter(())
 def __init__(self,*args):self.params={}
 def declare_parameter(self,k,v):self.params[k]=Param(v)
 def get_parameter(self,k):return self.params[k]
 def create_publisher(self,*a):return Pub()
 def create_subscription(self,*a):pass
 def get_logger(self):return Mock()
class Msg:
 def __init__(self,**kw):self.__dict__.update(kw)
for name in ['rclpy','rclpy.node','rclpy.qos','rclpy.action','rclpy.clock','sensor_msgs','sensor_msgs.msg','std_msgs','std_msgs.msg','builtin_interfaces','builtin_interfaces.msg','control_msgs','control_msgs.action','trajectory_msgs','trajectory_msgs.msg']:
 sys.modules[name]=types.ModuleType(name)
sys.modules['rclpy.node'].Node=FakeNode
sys.modules['rclpy.clock'].Clock=lambda **kw:kw
sys.modules['rclpy.clock'].ClockType=types.SimpleNamespace(STEADY_TIME=1)
sys.modules['rclpy.qos'].QoSProfile=lambda **kw:kw
sys.modules['rclpy.qos'].DurabilityPolicy=types.SimpleNamespace(TRANSIENT_LOCAL=1)
sys.modules['rclpy.qos'].ReliabilityPolicy=types.SimpleNamespace(BEST_EFFORT=1)
sys.modules['rclpy.action'].ActionClient=Mock
sys.modules['sensor_msgs.msg'].JointState=Msg
sys.modules['std_msgs.msg'].String=Msg
sys.modules['builtin_interfaces.msg'].Duration=Msg
sys.modules['control_msgs.action'].FollowJointTrajectory=Mock
sys.modules['trajectory_msgs.msg'].JointTrajectoryPoint=Msg
from satranc_robotu.web_gateway import WebGateway
from satranc_robotu.move_executor import MoveExecutor
from satranc_robotu.chess_engine_node import ChessEngine
from aiohttp import web,WSServerHandshakeError
from aiohttp.test_utils import TestServer,TestClient

class ExecutionTests(unittest.TestCase):
 def worker(self, success):
  n=MoveExecutor.__new__(MoveExecutor);n.arm=Mock();n.grip=Mock();n.say=Mock();n.report_state=Mock()
  n.g=Mock();n.g.home_xyz.return_value=(0,0,0);n.move_to=Mock(return_value=True);n.pick_place=Mock(return_value=success)
  import queue
  n.jobs=queue.Queue();n.jobs.put(('e2e4',[('P',('sq','e2'),('sq','e4'))],{'w':[],'b':[]}))
  n.confirmed_board=chess.Board();n.done_pub=Pub()
  sys.modules['rclpy'].ok=Mock(side_effect=[True,False]);n.worker();return n
 def test_failure_never_publishes_move_done_or_advances_board(self):
  n=self.worker(False);self.assertEqual(n.done_pub.messages,[]);self.assertEqual(n.confirmed_board,chess.Board())
  self.assertEqual(n.move_to.call_count,1) # no blind recovery motion
  self.assertFalse(n.report_state.call_args.kwargs['ready'])
 def test_success_confirms_board_and_publishes_done(self):
  n=self.worker(True);self.assertEqual(n.done_pub.messages,['e2e4']);self.assertEqual(n.confirmed_board.peek().uci(),'e2e4')
 def test_engine_waits_for_matching_physical_completion(self):
  n=ChessEngine.__new__(ChessEngine);n.board=chess.Board();n.robot_white=False;n.pending_human=None;n.early_human_done=None
  n.get_logger=Mock(return_value=Mock());n.robot_move=Mock();n.report_end=Mock(return_value=False)
  n.on_human(Msg(data='e2e4'));n.robot_move.assert_not_called()
  n.on_done(Msg(data='a2a4'));n.robot_move.assert_not_called()
  n.on_done(Msg(data='e2e4'));n.robot_move.assert_called_once()

class CompletionOrderTests(unittest.TestCase):
 def test_human_completion_can_arrive_before_human_topic(self):
  n=ChessEngine.__new__(ChessEngine);n.board=chess.Board();n.robot_white=False
  n.pending_human=None;n.early_human_done=None
  n.get_logger=Mock(return_value=Mock());n.robot_move=Mock();n.report_end=Mock(return_value=False)
  n.on_done(Msg(data='e2e4'));n.robot_move.assert_not_called()
  n.on_human(Msg(data='e2e4'));n.robot_move.assert_called_once()

class SocketTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.n=WebGateway();s={'session':'test','style':'alu','ready':True,'busy':False,'error':None,'fen':chess.Board().fen()}
  self.n.gate.observe(s);self.n.gate.joints_at=self.n.gate.clock()
  app=web.Application();app.router.add_get('/ws',self.n.socket)
  self.client=TestClient(TestServer(app));await self.client.start_server()
  self.origin=str(self.client.make_url('')).rstrip('/')
 async def asyncTearDown(self):await self.client.close()
 async def test_remote_key_rejected_before_state_is_sent(self):
  self.n.access_key='test-key-only'
  a=await self.client.ws_connect('/ws',headers={'Origin':self.origin})
  await a.send_json({'type':'auth','key':'wrong'})
  msg=await a.receive()
  self.assertEqual(msg.type,8)
  self.assertEqual(self.n.move_pub.messages,[])
  await a.close()
 async def test_remote_key_unlocks_state(self):
  self.n.access_key='test-key-only'
  a=await self.client.ws_connect('/ws',headers={'Origin':self.origin})
  await a.send_json({'type':'auth','key':'test-key-only'})
  self.assertEqual((await a.receive_json())['type'],'state')
  await a.close()
 async def test_reset_requires_a_new_ros_session(self):
  import tempfile
  with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
   self.n.reset_file=str(Path(tmp)/'reset.request')
   self.assertEqual(self.n.submit({'type':'reset'})['type'],'resetting')
   self.assertTrue(Path(self.n.reset_file).is_file())
   self.assertFalse(self.n.snapshot()['can_move'])
   with self.assertRaises(ValueError):self.n.submit({'type':'move','uci':'e2e4'})
   new=dict(self.n.gate.state);new['session']='restarted'
   self.n.on_state(Msg(data=__import__('json').dumps(new)))
   self.assertIsNone(self.n.reset_session)
 async def test_two_clients_only_one_move_published(self):
  a=await self.client.ws_connect('/ws',headers={'Origin':self.origin});b=await self.client.ws_connect('/ws',headers={'Origin':self.origin})
  await a.receive_json();await b.receive_json()
  await a.send_json({'type':'move','uci':'e2e4'});self.assertEqual((await a.receive_json())['type'],'accepted')
  await b.send_json({'type':'move','uci':'d2d4'});self.assertEqual((await b.receive_json())['type'],'error')
  self.assertEqual(self.n.move_pub.messages,['e2e4']);await a.close();await b.close()
 async def test_foreign_origin_rejected(self):
  with self.assertRaises(WSServerHandshakeError):await self.client.ws_connect('/ws',headers={'Origin':'https://unrelated.example'})
 async def test_illegal_move_does_not_publish(self):
  a=await self.client.ws_connect('/ws',headers={'Origin':self.origin});await a.receive_json()
  await a.send_json({'type':'move','uci':'e2e5'});self.assertEqual((await a.receive_json())['type'],'error')
  self.assertEqual(self.n.move_pub.messages,[]);await a.close()
 async def test_arbitrary_topic_command_rejected(self):
  a=await self.client.ws_connect('/ws',headers={'Origin':self.origin});await a.receive_json()
  await a.send_json({'type':'publish','topic':'/unsafe'});self.assertEqual((await a.receive_json())['type'],'error');await a.close()

if __name__=='__main__':unittest.main(verbosity=2)
