#!/usr/bin/env bash
# Gazebo fizik simülasyonunu başlatır (tahta, taşlar, robot kolu, denetleyiciler, satranç motoru).
# GPU_KONTROL.sh verified D3D12 hardware acceleration on this machine.
export GALLIUM_DRIVER=d3d12
source /opt/ros/lyrical/setup.bash
source ~/satranc_robotu_ws/install/setup.bash
ros2 launch satranc_robotu gazebo.launch.py style:="${1:-alu}" 2>&1 | tee /tmp/satranc_gazebo.log
