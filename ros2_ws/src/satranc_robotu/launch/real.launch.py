"""Gerçek robot (Raspberry Pi 5): denetleyiciler, hamle yürütücü, satranç motoru ve servo sürücü.

Çalıştırma:  ros2 launch satranc_robotu real.launch.py driver:=pca
             (driver: gpio = doğrudan GPIO, pca = PCA9685 kartı, dry = servo yok, yalnızca günlük)
İnsan hamlesini kendisi yapar ve '/human_move' konusuna yazar (sensör ya da elle):
             ros2 topic pub --once -w 2 /human_move std_msgs/String "{data: e2e4}"
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('satranc_robotu')
    xacro_file = PathJoinSubstitution([pkg, 'urdf', 'satranc_robotu.urdf.xacro'])
    robot_description = ParameterValue(Command(['xacro ', xacro_file, ' sim:=mock']), value_type=str)
    controllers_yaml = PathJoinSubstitution([pkg, 'config', 'controllers.yaml'])

    spawner = lambda name: Node(package='controller_manager', executable='spawner',
                                arguments=[name, '--param-file', controllers_yaml], output='screen')
    return LaunchDescription([
        DeclareLaunchArgument('driver', default_value='dry', description='gpio | pca | dry'),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot_description}], output='screen'),
        Node(package='controller_manager', executable='ros2_control_node', output='screen',
             parameters=[controllers_yaml], remappings=[('~/robot_description', '/robot_description')]),
        spawner('joint_state_broadcaster'),
        spawner('arm_controller'),
        spawner('gripper_controller'),
        Node(package='satranc_robotu', executable='move_executor', output='screen',
             parameters=[{'execute_human_moves': False}]),
        Node(package='satranc_robotu', executable='chess_engine', output='screen'),
        Node(package='satranc_robotu', executable='servo_driver', output='screen',
             parameters=[{'driver': LaunchConfiguration('driver')}]),
    ])
