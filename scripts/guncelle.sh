#!/usr/bin/env bash
# Windows'taki paket kopyasını Ubuntu'daki çalışma alanına aktarır ve yeniden derler (şifre gerekmez).
set -euo pipefail
BURASI="$(cd "$(dirname "$0")" && pwd)"
pkill -f "gz sim" 2>/dev/null || true
pkill -f "ros2 launch satranc_robotu" 2>/dev/null || true
rm -rf ~/satranc_robotu_ws/src/satranc_robotu
cp -r "$BURASI/../ros2_ws/src/satranc_robotu" ~/satranc_robotu_ws/src/
source /opt/ros/lyrical/setup.bash
cd ~/satranc_robotu_ws
colcon build --symlink-install 2>&1 | tail -3
