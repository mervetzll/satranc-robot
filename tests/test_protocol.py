import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
import unittest
import importlib.util
spec=importlib.util.spec_from_file_location('protocol', str(ROOT/'ros2_ws/src/satranc_robotu/satranc_robotu/web_protocol.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class GateTests(unittest.TestCase):
 def setUp(self):
  self.now=100.; self.g=m.CommandGate(lambda:self.now)
  self.state={'session':'a','style':'alu','ready':True,'busy':False,'error':None,'fen':'8/8/8/8/8/8/8/8 w - - 0 1'}
  self.g.observe(dict(self.state));self.g.joints_at=self.now
 def test_missing_state_rejected(self):
  self.assertIsNotNone(m.CommandGate().reason(2))
 def test_two_simultaneous_commands_only_one_accepted(self):
  self.g.reserve('e2e4',2)
  with self.assertRaises(ValueError): self.g.reserve('d2d4',2)
 def test_stale_joint_data_blocks(self):
  self.now+=4;self.g.observe(dict(self.state));self.assertIsNotNone(self.g.reason(2))
 def test_stale_executor_blocks(self):
  self.now+=4;self.g.joints_at=self.now;self.assertIsNotNone(self.g.reason(2))
 def test_wait_for_robot_turn(self):
  s=dict(self.state);s['fen']=s['fen'].replace(' w ',' b ');self.g.observe(s)
  self.assertIsNotNone(self.g.reason(2))
 def test_failed_motion_blocks(self):
  s=dict(self.state);s['error']='trajectory failed';self.g.observe(s)
  with self.assertRaises(ValueError):self.g.reserve('e2e4',2)
 def test_timeout_does_not_retry_automatically(self):
  self.g.reserve('e2e4',2);self.now+=11;self.g.observe(dict(self.state));self.g.joints_at=self.now
  self.assertIsNotNone(self.g.reason(2));self.assertIsNotNone(self.g.fault)
 def test_ros_restart_clears_old_session(self):
  self.g.reserve('e2e4',2);s=dict(self.state);s['session']='b';self.g.observe(s)
  self.assertIsNone(self.g.pending);self.assertIsNone(self.g.reason(2))
 def test_readiness_requires_both_subscribers(self):
  self.assertIsNotNone(self.g.reason(1));self.assertIsNone(self.g.reason(2))

if __name__=='__main__':unittest.main(verbosity=2)
