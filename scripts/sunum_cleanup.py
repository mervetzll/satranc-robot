"""Stop only this user's chess-project ROS/Gazebo processes and descendants."""
import os
import signal
import time
from pathlib import Path


def identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
        return fields[19], fields[0], int(fields[1])
    except (OSError, IndexError):
        return None


def select_project_processes(records, protected):
    selected = set()
    roles = {'move_executor', 'chess_engine', 'web_gateway', 'robot_state_publisher',
             'parameter_bridge', 'spawner', 'rviz2'}
    for pid, record in records.items():
        if pid in protected:
            continue
        argv, env, comm = record['argv'], record['env'], record['comm']
        command = ' '.join(argv)
        project_context = ('satranc_robotu' in env.get('AMENT_PREFIX_PATH', '') or
                           env.get('GZ_PARTITION', '').startswith('satranc_') or
                           'satranc_robotu' in command)
        project_launcher = ('launch satranc_robotu ' in command or
                            any(Path(arg).name == 'sunum_runner.py' for arg in argv[:3]))
        role = comm.startswith('gz-sim') or any(Path(arg).name in roles for arg in argv[:3])
        if project_launcher or (project_context and role):
            selected.add(pid)
    changed = True
    while changed:
        changed = False
        for pid, record in records.items():
            if pid not in protected and pid not in selected and record['identity'][2] in selected:
                selected.add(pid)
                changed = True
    return selected


def main():
    records = {}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            pid = int(entry.name)
            ident = identity(pid)
            if ident is None:
                continue
            argv = [v.decode(errors='replace') for v in (entry/'cmdline').read_bytes().split(b'\0') if v]
            # Keep only project-identification variables; never print credentials.
            env = {}
            for item in (entry/'environ').read_bytes().split(b'\0'):
                k, _, v = item.partition(b'=')
                if k in (b'AMENT_PREFIX_PATH', b'GZ_PARTITION'):
                    env[k.decode()] = v.decode(errors='replace')
            records[pid] = {'argv':argv, 'env':env, 'comm':(entry/'comm').read_text().strip(), 'identity':ident}
        except (OSError, ValueError):
            continue
    protected = set()
    pid = os.getpid()
    while pid and pid not in protected:
        protected.add(pid)
        ident = identity(pid)
        pid = ident[2] if ident else 0
    selected = select_project_processes(records, protected)

    def still_same(pid):
        now = identity(pid)
        return now and now[0] == records[pid]['identity'][0] and now[1] != 'Z'

    print('Önceki satranç projesi süreçleri kapatılıyor:', len(selected), flush=True)
    for pid in sorted(selected):
        if still_same(pid):
            print(pid, records[pid]['comm'], flush=True)
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline and any(still_same(pid) for pid in selected):
        time.sleep(0.2)
    for pid in selected:
        if still_same(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    print('Proje süreçlerinin temizliği tamamlandı. Dosya veya kilit silinmedi.', flush=True)


if __name__ == '__main__':
    main()
