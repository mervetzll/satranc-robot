"""Yalnızca RViz: kol modelini kaydırma çubuklarıyla eklem eklem oynatmak için.

Çalıştırma:  ros2 launch satranc_robotu display.launch.py
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('satranc_robotu')
    xacro_file = PathJoinSubstitution([pkg, 'urdf', 'satranc_robotu.urdf.xacro'])
    robot_description = ParameterValue(Command(['xacro ', xacro_file, ' sim:=mock style:=', LaunchConfiguration('style')]), value_type=str)
    return LaunchDescription([DeclareLaunchArgument('style', default_value='alu', choices=['alu', 'pink']),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot_description}]),
        Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui'),
        Node(package='rviz2', executable='rviz2',
             arguments=['-d', PathJoinSubstitution([pkg, 'rviz', 'satranc.rviz'])],
             additional_env={'QT_QPA_PLATFORM': 'xcb'}),
    ])
