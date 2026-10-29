#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source /opt/ros/lyrical/setup.bash
source "$HOME/satranc_robotu_ws/install/setup.bash"
exec ros2 run satranc_robotu web_gateway --ros-args -p "web_root:=$HERE/../web" "$@"
