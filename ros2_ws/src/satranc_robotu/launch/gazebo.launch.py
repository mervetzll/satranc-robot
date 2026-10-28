"""Gazebo fizik simülasyonu: tahta, 34 taş, robot kolu, denetleyiciler, hamle yürütücü ve satranç motoru.

Çalıştırma:  ros2 launch satranc_robotu gazebo.launch.py
Hamle yapma: ros2 topic pub --once -w 2 /human_move std_msgs/String "{data: e2e4}"
"""
import math

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

from satranc_robotu.geometry import Geometry
from satranc_robotu.world_models import board_sdf, piece_sdf, start_pieces


def generate_launch_description():
    g = Geometry()
    pkg = FindPackageShare('satranc_robotu')
    xacro_file = PathJoinSubstitution([pkg, 'urdf', 'satranc_robotu.urdf.xacro'])
    robot_description = ParameterValue(Command(['xacro ', xacro_file, ' sim:=gz']), value_type=str)
    sim_time = {'use_sim_time': True}

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])),
        launch_arguments={'gz_args': '-r empty.sdf'}.items(),
    )
    rsp = Node(package='robot_state_publisher', executable='robot_state_publisher',
               parameters=[{'robot_description': robot_description}, sim_time], output='screen')
    clock = Node(package='ros_gz_bridge', executable='parameter_bridge',
                 arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'], output='screen')

    # Robot 8. sıranın arkasında, tahtaya (−y) bakarak durur
    bx, by = g.base_xy()
    spawn_robot = Node(package='ros_gz_sim', executable='create', output='screen',
                       arguments=['-topic', 'robot_description', '-name', 'satranc_robotu',
                                  '-x', str(bx), '-y', str(by), '-z', '0', '-Y', str(-math.pi / 2)])
    spawn_board = Node(package='ros_gz_sim', executable='create', output='screen',
                       arguments=['-name', 'tahta', '-string', board_sdf(g)])
    spawn_pieces = [
        Node(package='ros_gz_sim', executable='create',
             arguments=['-name', name, '-string', piece_sdf(g, kind, color),
                        '-x', str(x), '-y', str(y), '-z', str(g.board_top)])
        for name, kind, color, x, y in start_pieces(g)
    ]

    # Denetleyici ayarları (eklem listeleri) spawner'a ayrıca verilmeli; yoksa 'joints' boş kalır
    controllers_yaml = PathJoinSubstitution([pkg, 'config', 'controllers.yaml'])
    spawner = lambda name: Node(package='controller_manager', executable='spawner',
                                arguments=[name, '--param-file', controllers_yaml], parameters=[sim_time], output='screen')
    controllers = RegisterEventHandler(OnProcessExit(
        target_action=spawn_robot,
        on_exit=[spawner('joint_state_broadcaster'), spawner('arm_controller'), spawner('gripper_controller')],
    ))

    executor = Node(package='satranc_robotu', executable='move_executor', output='screen',
                    parameters=[sim_time, {'execute_human_moves': True}])
    engine = Node(package='satranc_robotu', executable='chess_engine', output='screen', parameters=[sim_time])
    # WSL'in Wayland ekranında RViz pencere açamıyor; X11 (xcb) ile açılır
    rviz = Node(package='rviz2', executable='rviz2', parameters=[sim_time],
                arguments=['-d', PathJoinSubstitution([pkg, 'rviz', 'satranc.rviz'])],
                additional_env={'QT_QPA_PLATFORM': 'xcb'})

    return LaunchDescription([gazebo, rsp, clock, spawn_robot, spawn_board, *spawn_pieces,
                              controllers, executor, engine, rviz])
