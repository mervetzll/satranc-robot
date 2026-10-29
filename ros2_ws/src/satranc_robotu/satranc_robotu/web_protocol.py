"""Command gate shared by the ROS adapter and offline tests. Wall-clock freshness."""
import time


class CommandGate:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.state = None
        self.state_at = self.joints_at = float('-inf')
        self.pending = None
        self.fault = None

    def observe(self, state):
        old = self.state
        if old and old['session'] != state['session']:
            self.pending = None
            self.fault = None
        if self.pending and (state.get('busy') or state.get('error') or
                             state['fen'] != self.pending['fen']):
            self.pending = None
        self.state, self.state_at = state, self.clock()

    def reason(self, subscribers):
        now = self.clock()
        if self.pending and now - self.pending['at'] > 10:
            self.fault = 'Komutun ROS tarafından alındığı doğrulanamadı; ağ geçidini yeniden başlatın.'
        if self.fault:
            return self.fault
        if not self.state or now - self.state_at > 3:
            return 'ROS yürütücü verisi bekleniyor veya bağlantı kesildi'
        if now - self.joints_at > 3:
            return 'Güncel eklem verisi bekleniyor'
        if self.state.get('error'):
            return self.state['error']
        if not self.state.get('ready'):
            return 'Robot başlangıç konumuna hazırlanıyor'
        if self.state.get('busy') or self.pending:
            return 'Hareket devam ediyor'
        if subscribers < 2:
            return 'Hamle yürütücü ve satranç motoru hazır değil'
        if self.state['fen'].split()[1] != 'w':
            return 'Robotun karşı hamlesi bekleniyor'
        return None

    def reserve(self, uci, subscribers):
        reason = self.reason(subscribers)
        if reason:
            raise ValueError(reason)
        self.pending = {'uci': uci, 'fen': self.state['fen'], 'at': self.clock()}
