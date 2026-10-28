#!/usr/bin/env bash
# Gazebo fizik simülasyonunu başlatır (tahta, taşlar, robot kolu, denetleyiciler, satranç motoru).
source /opt/ros/lyrical/setup.bash
source ~/satranc_robotu_ws/install/setup.bash
ros2 launch satranc_robotu gazebo.launch.py 2>&1 | tee /tmp/satranc_gazebo.log
