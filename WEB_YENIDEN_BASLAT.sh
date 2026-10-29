#!/usr/bin/env bash
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$HOME/satranc_robotu_codex_ws"
source /opt/ros/lyrical/setup.bash
cp "$ROOT/ros2_ws/src/satranc_robotu/satranc_robotu/web_gateway.py" "$WS/src/satranc_robotu/satranc_robotu/web_gateway.py"
cd "$WS"
colcon build --symlink-install --packages-select satranc_robotu
source "$WS/install/setup.bash"
export ROS_DOMAIN_ID=42
export GZ_PARTITION=satranc_codex_test
export ROS_LOCALHOST_ONLY=1
mkdir -p "$WS/test-logs"
echo 'Web bağlantısı açılıyor: http://localhost:8080/'
ros2 run satranc_robotu web_gateway --ros-args -p "web_root:=$ROOT/web" 2>&1 | tee "$WS/test-logs/web.log"
