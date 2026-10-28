"""Satranç motoru düğümü.

'/human_move' konusundan insanın hamlesini (UCI, örn. "e2e4") alır, kurala uygunluğunu
denetler, Stockfish ile robotun cevabını seçer ve '/chess_move' konusuna yayınlar.
Stockfish kurulu değilse rastgele bir yasal hamle seçer ve uyarır.
"""
import random

import chess
import chess.engine
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ChessEngine(Node):
    def __init__(self):
        super().__init__('chess_engine')
        self.declare_parameter('stockfish_path', '/usr/games/stockfish')
        self.declare_parameter('think_time', 0.5)       # saniye
        self.declare_parameter('robot_color', 'black')  # 'white' ya da 'black'
        self.think = self.get_parameter('think_time').value
        self.robot_white = self.get_parameter('robot_color').value == 'white'
        self.board = chess.Board()
        self.engine = None
        path = self.get_parameter('stockfish_path').value
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(path)
            self.get_logger().info(f'Stockfish açıldı: {path}')
        except (FileNotFoundError, OSError, chess.engine.EngineError):
            self.get_logger().warn('Stockfish bulunamadı; robot rastgele yasal hamle oynayacak. Kurulum: sudo apt install stockfish')
        self.move_pub = self.create_publisher(String, '/chess_move', 10)
        self.create_subscription(String, '/human_move', self.on_human, 10)
        if self.robot_white:
            self.create_timer(2.0, self.first_move)

    def first_move(self):
        if self.board.move_stack:
            return
        self.robot_move()

    def on_human(self, msg):
        try:
            move = chess.Move.from_uci(msg.data.strip())
        except ValueError:
            self.get_logger().error(f'Hamle okunamadı: {msg.data}')
            return
        if move not in self.board.legal_moves:
            self.get_logger().error(f'Kurala aykırı hamle: {msg.data}')
            return
        self.board.push(move)
        if not self.report_end():
            self.robot_move()

    def robot_move(self):
        if self.engine is not None:
            move = self.engine.play(self.board, chess.engine.Limit(time=self.think)).move
        else:
            move = random.choice(list(self.board.legal_moves))
        self.board.push(move)
        self.move_pub.publish(String(data=move.uci()))
        self.get_logger().info(f'Robotun hamlesi: {move.uci()}')
        self.report_end()

    def report_end(self):
        if not self.board.is_game_over():
            return False
        self.get_logger().info(f'Oyun bitti: {self.board.result()} ({self.board.outcome().termination.name})')
        return True

    def destroy_node(self):
        if self.engine is not None:
            self.engine.quit()
        super().destroy_node()


def main():
    rclpy.init()
    node = ChessEngine()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
