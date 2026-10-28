from glob import glob

from setuptools import setup

package_name = 'satranc_robotu'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/urdf', glob('urdf/*.xacro')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/rviz', glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Gül Merve Tezel',
    maintainer_email='209282102+mervetzll@users.noreply.github.com',
    description='Satranç oynayan 5 eksenli servo kol için ROS 2 paketi',
    license='MIT',
    entry_points={
        'console_scripts': [
            'move_executor = satranc_robotu.move_executor:main',
            'chess_engine = satranc_robotu.chess_engine_node:main',
            'servo_driver = satranc_robotu.servo_driver_node:main',
        ],
    },
)
