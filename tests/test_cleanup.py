import importlib.util
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).resolve().parents[1]/'scripts'/'sunum_cleanup.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)

def record(argv, parent=0, env=None, comm='python3'):
    return {'argv':argv, 'env':env or {}, 'comm':comm, 'identity':('100','S',parent)}

class CleanupTests(unittest.TestCase):
    def test_unrelated_processes_survive(self):
        rows={1:record(['python3','server.py']),2:record(['spawner']),3:record(['gz'],comm='gz-sim-server')}
        self.assertEqual(cleanup.select_project_processes(rows,set()),set())
    def test_launcher_and_descendants(self):
        rows={1:record(['ros2','launch','satranc_robotu','gazebo.launch.py']),2:record(['child'],1),3:record(['grandchild'],2),4:record(['other'])}
        self.assertEqual(cleanup.select_project_processes(rows,set()),{1,2,3})
    def test_protected_process_survives(self):
        rows={1:record(['python3','sunum_runner.py']),2:record(['child'],1)}
        self.assertEqual(cleanup.select_project_processes(rows,{2}),{1})
        self.assertEqual(cleanup.select_project_processes(rows,{1,2}),set())
    def test_gazebo_requires_project_evidence(self):
        rows={1:record(['gz'],env={'GZ_PARTITION':'satranc_sunum_42'},comm='gz-sim-server'),2:record(['gz'],env={'GZ_PARTITION':'other'},comm='gz-sim-server')}
        self.assertEqual(cleanup.select_project_processes(rows,set()),{1})
    def test_orphan_node_with_project_context(self):
        rows={1:record(['/opt/ros/bin/spawner'],env={'AMENT_PREFIX_PATH':'/home/user/satranc_robotu_codex_ws/install/satranc_robotu'}),2:record(['/opt/ros/bin/spawner'])}
        self.assertEqual(cleanup.select_project_processes(rows,set()),{1})

if __name__=='__main__': unittest.main()
