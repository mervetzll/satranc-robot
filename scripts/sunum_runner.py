"""Owns one presentation simulation, gateway and temporary HTTPS tunnel (Linux)."""
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path.home() / 'satranc_robotu_codex_ws' / '.sunum'
RUNTIME.mkdir(parents=True, exist_ok=True)
os.chmod(RUNTIME, 0o700)
SITE = 'https://mervetzll.github.io/satranc-robot'
SITE_ORIGIN = 'https://' + urlsplit(SITE).netloc
STYLE = sys.argv[1] if len(sys.argv) > 1 else 'pink'
if STYLE not in ('pink', 'alu'):
    raise SystemExit('Tasarım pink veya alu olmalı')
with socket.socket() as probe:
    if probe.connect_ex(('127.0.0.1', 8080)) == 0:
        raise SystemExit('8080 portu kullanımda. Önce eski web sunucusunun terminalinde Ctrl+C yapın.')
cloudflared = shutil.which('cloudflared') or str(RUNTIME / 'cloudflared')
if not Path(cloudflared).is_file():
    raise SystemExit('Cloudflared bulunamadı. SUNUM_BASLAT.sh kullanın.')
key = secrets.token_urlsafe(24)
keyfile = RUNTIME / 'access.key'
fd = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write(key)
reset_file = RUNTIME / 'reset.request'
reset_file.unlink(missing_ok=True)
env = os.environ.copy()
session_ros_home = RUNTIME / f'ros-home-{os.getpid()}'
session_ros_home.mkdir(parents=True, exist_ok=True)
env.update(ROS_HOME=str(session_ros_home), QT_QPA_PLATFORM='xcb', ROS_DOMAIN_ID='87', GZ_PARTITION=f'satranc_sunum_{os.getpid()}',
           ROS_LOCALHOST_ONLY='1', GALLIUM_DRIVER='d3d12',
           SATRANC_CONTROL_KEY=key, SATRANC_RESET_FILE=str(reset_file))
processes = []
streams = []

def start(args, logname):
    stream = (RUNTIME / logname).open('w')
    streams.append(stream)
    proc = subprocess.Popen(args, env=env, stdout=stream, stderr=subprocess.STDOUT,
                            start_new_session=True)
    processes.append(proc)
    return proc


def stop(proc):
    if proc.poll() is not None:
        return
    os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


def start_sim():
    return start(['ros2', 'launch', 'satranc_robotu', 'gazebo.launch.py',
                  f'style:={STYLE}', 'rviz:=false'], 'gazebo.log')


def interrupted(signum, frame):
    raise KeyboardInterrupt

signal.signal(signal.SIGTERM, interrupted)
try:
    gateway = start(['ros2', 'run', 'satranc_robotu', 'web_gateway', '--ros-args',
                     '-p', f'web_root:={ROOT / "web"}', '-p', f'allowed_origin:={SITE_ORIGIN}'], 'web.log')
    for _ in range(100):
        if gateway.poll() is not None:
            raise RuntimeError('Web sunucusu açılamadı: ' + (RUNTIME / 'web.log').read_text()[-3000:])
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', 8080)) == 0:
                break
        time.sleep(0.1)
    else:
        raise RuntimeError('Web sunucusu 10 saniyede hazır olmadı')
    sim = start_sim()
    tunnel = start([cloudflared, 'tunnel', '--no-autoupdate', '--url', 'http://127.0.0.1:8080'], 'tunnel.log')
    print('Pembe/alüminyum ROS sunumu başlatılıyor. Başlangıç konumu bekleniyor.', flush=True)
    print('SUNUM ANAHTARI (yalnızca kontrol edecek kişiyle paylaşın): ' + key, flush=True)
    print('Yerel arayüz: http://localhost:8080/', flush=True)
    print('Sunum kapanana kadar bu terminal açık kalmalı. Ctrl+C hepsini durdurur.', flush=True)
    announced = False
    while True:
        if gateway.poll() is not None:
            raise RuntimeError('Web sunucusu kapandı; .sunum/web.log dosyasını kontrol edin')
        if sim.poll() is not None:
            raise RuntimeError('ROS/Gazebo kapandı; .sunum/gazebo.log dosyasını kontrol edin')
        if not announced:
            text = (RUNTIME / 'tunnel.log').read_text(errors='replace')
            match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', text)
            if match:
                endpoint = match.group(0).replace('https://', 'wss://') + '/ws'
                shared = SITE + '/simulator.html#endpoint=' + quote(endpoint, safe='')
                report = 'SUNUM BAGLANTISI: ' + shared + '\nWSS: ' + endpoint + '\nAnahtar bu dosyada saklanmaz. Terminalde gösterilir.\n'
                (ROOT / 'SUNUM_BAGLANTISI.txt').write_text(report, encoding='utf-8')
                print('\nHOCAYA GÖNDERİLECEK CANLI SUNUM BAĞLANTISI:\n' + shared, flush=True)
                announced = True
        if tunnel.poll() is not None:
            (ROOT / 'SUNUM_BAGLANTISI.txt').write_text('Uzak bağlantı kapalı. Yeni canlı bağlantı için sunumu yeniden başlatın.\n', encoding='utf-8')
            raise RuntimeError('Cloudflare tüneli kapandı; uzak sunum durduruluyor. .sunum/tunnel.log kontrol edilmeli.')
        if reset_file.exists():
            reset_file.unlink(missing_ok=True)
            print('Yalnızca bu sunuma ait Gazebo ve oyun düğümleri sıfırlanıyor…', flush=True)
            stop(sim)
            time.sleep(1)
            sim = start_sim()
            print('Yeni Gazebo dünyası açılıyor; web sayfası yeni ROS oturumunu bekleyecek.', flush=True)
        time.sleep(0.3)
except KeyboardInterrupt:
    print('\nSunum kapatılıyor.', flush=True)
except Exception as exc:
    print(str(exc), file=sys.stderr, flush=True)
    raise SystemExit(1)
finally:
    for proc in reversed(processes):
        stop(proc)
    for stream in streams:
        stream.close()
    keyfile.unlink(missing_ok=True)
