#!/usr/bin/env bash
# Run from the user's Ubuntu terminal. Keeps the previous workspace untouched.
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$HOME/satranc_robotu_codex_ws"
LOG="$WS/test-logs"
STYLE="${1:-pink}"
case "$STYLE" in pink|alu) ;; *) echo 'Tasarım pink veya alu olmalı.'; exit 1;; esac
if [ ! -f /opt/ros/lyrical/setup.bash ]; then
  echo 'ROS 2 Lyrical bulunamadı: /opt/ros/lyrical/setup.bash'; exit 1
fi
# GPU_KONTROL.sh verified D3D12 hardware acceleration on this machine.
export GALLIUM_DRIVER=d3d12
source /opt/ros/lyrical/setup.bash
# A separate ROS domain and Gazebo partition avoid mixing with another session.
export ROS_DOMAIN_ID=42
export GZ_PARTITION=satranc_codex_test
export ROS_LOCALHOST_ONLY=1
if ! python3 -c 'import aiohttp, chess' 2>/dev/null; then
  echo 'Python bağımlılığı eksik. Önce sudo apt install python3-aiohttp çalıştırın.'
  echo 'chess de eksikse: python3 -I scripts/chess_kur.py'
  exit 1
fi
mkdir -p "$WS/src/satranc_robotu" "$LOG"
cp -r "$ROOT/ros2_ws/src/satranc_robotu/." "$WS/src/satranc_robotu/"
cd "$WS"
echo '=== GELİŞTİRME PAKETİ DERLENİYOR ==='
colcon build --symlink-install --packages-select satranc_robotu 2>&1 | tee "$LOG/build.log"
source "$WS/install/setup.bash"
echo '=== WEB BAĞLANTISI BAŞLATILIYOR ==='
ros2 run satranc_robotu web_gateway --ros-args -p "web_root:=$ROOT/web" > "$LOG/web.log" 2>&1 &
GATEWAY_PID=$!
cleanup() { kill "$GATEWAY_PID" 2>/dev/null || true; }
trap cleanup EXIT
sleep 2
if ! kill -0 "$GATEWAY_PID" 2>/dev/null; then
  cat "$LOG/web.log"; echo 'Web sunucusu açılamadı; Gazebo başlatılmadı.'; exit 1
fi
echo '=== GAZEBO BAŞLATILIYOR ==='
echo "Tasarım: $STYLE | ROS domain: $ROS_DOMAIN_ID"
echo 'Site: http://localhost:8080/ — ROS’a bağlan düğmesine basın.'
echo 'Kol hazır olmadan Oynat açılmaz. Durdurmak için Ctrl+C.'
echo "Günlükler: $LOG"
ros2 launch satranc_robotu gazebo.launch.py "style:=$STYLE" 2>&1 | tee "$LOG/gazebo.log"
