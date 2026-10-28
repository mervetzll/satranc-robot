#!/usr/bin/env bash
# Kullanım: bash hamle.sh e2e4   → beyazın hamlesini simülasyona gönderir
source /opt/ros/lyrical/setup.bash
source ~/satranc_robotu_ws/install/setup.bash
# -w 2: hamle yürütücü ve satranç motoru, ikisi de dinlemeye başlayana kadar bekle
ros2 topic pub --once -w 2 /human_move std_msgs/msg/String "{data: $1}"
