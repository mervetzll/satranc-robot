#!/usr/bin/env bash
# Kurulumun durumunu okur; hiçbir şeyi değiştirmez.
source /opt/ros/lyrical/setup.bash
source ~/satranc_robotu_ws/install/setup.bash
echo "ROS: $ROS_DISTRO"
ros2 pkg list 2>/dev/null | grep -E "^(satranc_robotu|ros_gz_sim|gz_ros2_control|joint_trajectory_controller|controller_manager|xacro)$"
echo "---"
which gz stockfish
python3 --version
python3 -c "import chess; print('python-chess', chess.__version__)" 2>&1 | tail -1
echo "---"
xacro ~/satranc_robotu_ws/install/satranc_robotu/share/satranc_robotu/urdf/satranc_robotu.urdf.xacro sim:=gz > /tmp/robot.urdf && echo "xacro tamam: $(grep -c '<link' /tmp/robot.urdf) link, $(grep -c '<joint' /tmp/robot.urdf) eklem"
