"""Satranç robotunun geometrisi: tahta, taşlar, bölmeler ve ters kinematik.

Tarayıcı simülatöründeki hesapların aynısıdır; tek fark uzunlukların metre olmasıdır.
Koordinatlar: tahtanın merkezi (0, 0), x ekseni a → h sütunu, y ekseni 1 → 8. sıra,
z ekseni yukarı (zemin = 0). Robot 8. sıranın arkasında durur ve tahtaya (−y) bakar.
"""
import math
from dataclasses import dataclass

FILES = 'abcdefgh'

# Staunton oranları: (boy / kare kenarı, taban çapı / kare kenarı)
PIECE = {
    'K': (1.75, 0.78), 'Q': (1.55, 0.76), 'B': (1.30, 0.70),
    'N': (1.20, 0.70), 'R': (1.05, 0.70), 'P': (0.95, 0.60),
}


def _wrap(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a <= -math.pi:
        a += 2 * math.pi
    return a


@dataclass
class Geometry:
    s: float = 0.05            # kare kenarı
    base_gap: float = 0.095    # taban merkezi → tahta kenarı
    zone_gap: float = 0.01     # bölme ile tahta arası
    zone_cols: int = 4         # 4×4 bölme: yenebilecek 15 taşın hepsi sığar
    zone_rows: int = 4
    board_top: float = 0.006   # Gazebo'daki tahtanın üst yüzeyi
    L1: float = 0.10           # zemin → omuz ekseni
    L2: float = 0.24           # üst kol
    L3: float = 0.30           # ön kol
    L4: float = 0.14           # bilek → parmak ucu
    tilt_deg: float = 20.0     # tutucunun dikeyden eğimi
    grasp_frac: float = 0.45   # kavrama yüksekliği / taş boyu
    clearance: float = 0.03    # taşırken en uzun taşın üstünde bırakılan pay

    @property
    def half(self):
        return 4 * self.s

    def piece_h(self, t):
        return PIECE[t][0] * self.s

    def piece_d(self, t):
        return PIECE[t][1] * self.s

    def grasp_d(self, t):
        # kavrama noktasındaki gövde çapı (taban çapının %62'si, tahmin)
        return 0.62 * self.piece_d(t)

    def grasp_z(self, t):
        return self.board_top + self.grasp_frac * self.piece_h(t)

    def travel_z(self):
        # en uzun taşın tepesi + pay + taşınan taşın parmak ucundan sarkan kısmı
        return self.board_top + self.piece_h('K') + self.clearance + self.grasp_frac * self.piece_h('K')

    def square_xy(self, key):
        f, r = FILES.index(key[0]), int(key[1]) - 1
        return (-self.half + self.s * (f + 0.5), -self.half + self.s * (r + 0.5))

    def zone_xy(self, side, idx):
        c, r = idx % self.zone_cols, idx // self.zone_cols
        x = (self.half + self.zone_gap + self.s * (c + 0.5)) * (-1 if side == 'w' else 1)
        return (x, self.half - self.s * (r + 0.5))

    @property
    def zone_slots(self):
        return self.zone_cols * self.zone_rows

    def base_xy(self):
        return (0.0, self.half + self.base_gap)

    def board_to_base(self, x, y):
        """Tahta koordinatı → robot taban çerçevesi (ileri = +x, sol = +y)."""
        bx, by = self.base_xy()
        return (by - y, x - bx)

    def home_xyz(self):
        bx, by = self.base_xy()
        return (bx, by - 0.32, self.travel_z() + 0.02)

    def ik(self, x, y, z):
        """Parmak ucunun tahta koordinatındaki hedefi → (j1, j2, j3, j4, j5) radyan.

        j1 taban, j2 omuz (yataydan yukarı +), j3 dirsek ve j4 bilek bir önceki
        uzva göre (aşağı −), j5 çeneyi tahtanın köşegenine çevirir.
        Ulaşılamayan noktada None döner.
        """
        xb, yb = self.board_to_base(x, y)
        th1 = math.atan2(yb, xb)
        r = math.hypot(xb, yb)
        ph4 = -math.pi / 2 + math.radians(self.tilt_deg)
        wr = r - self.L4 * math.cos(ph4)
        dz = z - self.L4 * math.sin(ph4) - self.L1
        D = math.hypot(wr, dz)
        if D > self.L2 + self.L3 or D < abs(self.L2 - self.L3) + 1e-4:
            return None
        a = math.atan2(dz, wr)
        b = math.acos(max(-1.0, min(1.0, (self.L2 ** 2 + D ** 2 - self.L3 ** 2) / (2 * self.L2 * D))))
        th2 = a + b
        ex, ez = self.L2 * math.cos(th2), self.L2 * math.sin(th2)
        ph3 = math.atan2(dz - ez, wr - ex)
        q3 = _wrap(ph3 - th2)
        q4 = _wrap(ph4 - ph3)
        psi = th1 - math.pi / 4
        while psi > math.pi / 4:
            psi -= math.pi / 2
        while psi < -math.pi / 4:
            psi += math.pi / 2
        return (th1, th2, q3, q4, psi)


def joints_to_servo_deg(j):
    """Eklem açıları (rad) → servo açıları (0–180°). Tarayıcı simülatörüyle aynı eşleme."""
    d = [math.degrees(v) for v in j]
    return [90 + d[0], d[1], -d[2], 180 + d[3], 90 + d[4]]
