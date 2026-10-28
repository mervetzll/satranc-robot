"""Servo sürücü düğümü (gerçek robot, Raspberry Pi 5).

'/joint_states' konusundaki eklem açılarını servo açılarına çevirir (tarayıcı simülatörüyle
aynı eşleme) ve servolara yazar.
  driver:=gpio → gpiozero ile doğrudan GPIO (sürücü kartı yok; pinler: 12, 13, 18, 19, 23, 24)
  driver:=pca  → PCA9685 kartı (Adafruit ServoKit, kanal 0–5)
  driver:=dry  → servo yok, açıları yalnızca günlüğe yazar (deneme için)
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

from .geometry import joints_to_servo_deg

ARM_JOINTS = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5']


class ServoDriver(Node):
    def __init__(self):
        super().__init__('servo_driver')
        self.declare_parameter('driver', 'dry')
        self.declare_parameter('gpio_pins', [12, 13, 18, 19, 23, 24])  # J1..J5, tutucu
        self.declare_parameter('pca_channels', [0, 1, 2, 3, 4, 5])
        self.declare_parameter('rate', 50.0)                 # Hz
        self.declare_parameter('grip_closed_m', 0.006)       # parmak eklemi kapalı
        self.declare_parameter('grip_open_m', 0.025)         # parmak eklemi açık
        self.declare_parameter('grip_closed_deg', 20.0)      # tutucu servosu kapalı açı
        self.declare_parameter('grip_open_deg', 110.0)       # tutucu servosu açık açı
        self.declare_parameter('offsets_deg', [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # kalibrasyon farkları
        p = lambda n: self.get_parameter(n).value
        self.driver = p('driver')
        self.offsets = list(p('offsets_deg'))
        self.grip = (p('grip_closed_m'), p('grip_open_m'), p('grip_closed_deg'), p('grip_open_deg'))
        self.servos = self.open_servos(p('gpio_pins'), p('pca_channels'))
        self.latest = None
        self.log_count = 0
        self.create_subscription(JointState, '/joint_states', self.on_state, 10)
        self.create_timer(1.0 / p('rate'), self.write)

    def open_servos(self, pins, channels):
        if self.driver == 'gpio':
            from gpiozero import AngularServo
            return [AngularServo(pin, min_angle=0, max_angle=180, min_pulse_width=0.0005,
                                 max_pulse_width=0.0025, frame_width=0.02) for pin in pins]
        if self.driver == 'pca':
            from adafruit_servokit import ServoKit
            kit = ServoKit(channels=16)
            out = []
            for ch in channels:
                kit.servo[ch].set_pulse_width_range(500, 2500)
                out.append(kit.servo[ch])
            return out
        self.get_logger().info('driver=dry: servolar sürülmüyor, açılar günlüğe yazılıyor')
        return None

    def on_state(self, msg):
        pos = dict(zip(msg.name, msg.position))
        if all(n in pos for n in ARM_JOINTS):
            self.latest = ([pos[n] for n in ARM_JOINTS], pos.get('finger_left_joint'))

    def write(self):
        if self.latest is None:
            return
        joints, finger = self.latest
        angles = joints_to_servo_deg(joints)
        if finger is not None:
            c_m, o_m, c_d, o_d = self.grip
            k = (finger - c_m) / (o_m - c_m)
            angles.append(c_d + (o_d - c_d) * max(0.0, min(1.0, k)))
        angles = [max(0.0, min(180.0, a + off)) for a, off in zip(angles, self.offsets)]
        if self.servos is None:
            self.log_count += 1
            if self.log_count % 50 == 0:
                self.get_logger().info('servo açıları: ' + ', '.join(f'{a:.1f}' for a in angles))
            return
        for servo, a in zip(self.servos, angles):
            servo.angle = a


def main():
    rclpy.init()
    node = ServoDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
