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
        self.pending_human = None
        self.early_human_done = None
        self.engine = None
        path = self.get_parameter('stockfish_path').value
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(path)
            self.get_logger().info(f'Stockfish açıldı: {path}')
        except (FileNotFoundError, OSError, chess.engine.EngineError):
            self.get_logger().warn('Stockfish bulunamadı; robot rastgele yasal hamle oynayacak. Kurulum: sudo apt install stockfish')
        self.move_pub = self.create_publisher(String, '/chess_move', 10)
        self.create_subscription(String, '/human_move', self.on_human, 10)
        self.create_subscription(String, '/move_done', self.on_done, 10)
        if self.robot_white:
            self.create_timer(2.0, self.first_move)

    def first_move(self):
        if self.board.move_stack:
            return
        self.robot_move()

    def on_human(self, msg):
        if self.pending_human or self.board.turn == self.robot_white:
            self.get_logger().warn('Robotun sırası veya hareket devam ediyor')
            return
        try:
            move = chess.Move.from_uci(msg.data.strip())
        except ValueError:
            self.get_logger().error(f'Hamle okunamadı: {msg.data}')
            return
        if move not in self.board.legal_moves:
            self.get_logger().error(f'Kurala aykırı hamle: {msg.data}')
            return
        self.board.push(move)
        self.pending_human = move.uci()
        if self.early_human_done == self.pending_human:
            self.early_human_done = None
            self.on_done(msg)

    def on_done(self, msg):
        if msg.data != self.pending_human:
            # Separate topics have no cross-topic delivery order guarantee. This
            # can occur when a human physically moves the piece (real launch).
            if self.pending_human is None and self.board.turn != self.robot_white:
                try:
                    move = chess.Move.from_uci(msg.data)
                    if move in self.board.legal_moves:
                        self.early_human_done = msg.data
                except ValueError:
                    pass
            return
        self.pending_human = None
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
