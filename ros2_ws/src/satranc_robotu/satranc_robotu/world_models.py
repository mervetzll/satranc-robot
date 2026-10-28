"""Gazebo için tahta ve taş modelleri (SDF metni olarak üretilir).

Tahta durağan bir modeldir: 64 kare, iki bölme tepsisi. Taşlar fizik uygulanan iki
silindirden oluşur: geniş taban ve kavranan ince gövde. Ölçüler Geometry'den gelir.
"""
from .geometry import FILES, Geometry

WHITE = '0.93 0.90 0.84 1'
BLACK = '0.17 0.18 0.20 1'
LIGHT = '0.92 0.85 0.73 1'
DARK = '0.55 0.40 0.28 1'
TRAY = '0.36 0.26 0.19 1'
RESERVE = '0.91 0.78 0.66 1'


def _box_visual(name, x, y, z, sx, sy, sz, rgba):
    return (f'<visual name="{name}"><pose>{x} {y} {z} 0 0 0</pose>'
            f'<geometry><box><size>{sx} {sy} {sz}</size></box></geometry>'
            f'<material><ambient>{rgba}</ambient><diffuse>{rgba}</diffuse></material></visual>')


def board_sdf(g: Geometry):
    t, s, h = g.board_top, g.s, g.half
    size = 8 * s + 0.016  # 8 mm çerçeve
    parts = [
        f'<collision name="tahta"><pose>0 0 {t / 2} 0 0 0</pose>'
        f'<geometry><box><size>{size} {size} {t}</size></box></geometry></collision>',
        _box_visual('cerceve', 0, 0, t / 2 - 0.0005, size, size, t - 0.001, TRAY),
    ]
    for f in range(8):
        for r in range(8):
            x, y = g.square_xy(FILES[f] + str(r + 1))
            parts.append(_box_visual(f'kare_{FILES[f]}{r + 1}', x, y, t - 0.0005, s, s, 0.001,
                                     DARK if (f + r) % 2 == 0 else LIGHT))
    for side in ('w', 'b'):
        sign = -1 if side == 'w' else 1
        cx = sign * (h + g.zone_gap + g.zone_cols * s / 2)
        cy = h - g.zone_rows * s / 2
        sx, sy = g.zone_cols * s + 0.008, g.zone_rows * s + 0.008
        parts.append(f'<collision name="bolme_{side}"><pose>{cx} {cy} {t / 2} 0 0 0</pose>'
                     f'<geometry><box><size>{sx} {sy} {t}</size></box></geometry></collision>')
        parts.append(_box_visual(f'bolme_{side}', cx, cy, t / 2, sx, sy, t, TRAY))
        for i in range(g.zone_slots):
            x, y = g.zone_xy(side, i)
            parts.append(_box_visual(f'goz_{side}{i}', x, y, t + 0.0005, s * 0.92, s * 0.92, 0.001,
                                     RESERVE if i == 0 else LIGHT))
    return ('<?xml version="1.0"?><sdf version="1.9"><model name="tahta"><static>true</static>'
            '<link name="link">' + ''.join(parts) + '</link></model></sdf>')


def piece_sdf(g: Geometry, t, color, mass=0.040):
    hgt, rb, rg = g.piece_h(t), g.piece_d(t) / 2, g.grasp_d(t) / 2
    hb = 0.15 * hgt            # taban diskinin yüksekliği
    hg = hgt - hb              # kavranan gövdenin yüksekliği
    rgba = WHITE if color == 'w' else BLACK
    ixx = mass * (3 * rg * rg + hgt * hgt) / 12
    izz = mass * rg * rg / 2
    surface = '<surface><friction><ode><mu>1.5</mu><mu2>1.5</mu2></ode></friction></surface>'

    def cyl(name, r, length, z):
        geo = f'<geometry><cylinder><radius>{r}</radius><length>{length}</length></cylinder></geometry>'
        return (f'<collision name="{name}"><pose>0 0 {z} 0 0 0</pose>{geo}{surface}</collision>'
                f'<visual name="{name}"><pose>0 0 {z} 0 0 0</pose>{geo}'
                f'<material><ambient>{rgba}</ambient><diffuse>{rgba}</diffuse></material></visual>')

    return ('<?xml version="1.0"?><sdf version="1.9"><model name="tas"><link name="link">'
            f'<inertial><pose>0 0 {hgt / 2} 0 0 0</pose><mass>{mass}</mass>'
            f'<inertia><ixx>{ixx}</ixx><iyy>{ixx}</iyy><izz>{izz}</izz>'
            '<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>'
            + cyl('taban', rb, hb, hb / 2) + cyl('govde', rg, hg, hb + hg / 2)
            + '</link></model></sdf>')


def start_pieces(g: Geometry):
    """Başlangıç dizilişi + her bölmenin 0. gözündeki yedek vezir: (ad, tür, renk, x, y)."""
    back = 'RNBQKBNR'
    out = []
    for f in range(8):
        for color, rank, kind in (('w', 1, back[f]), ('w', 2, 'P'), ('b', 7, 'P'), ('b', 8, back[f])):
            x, y = g.square_xy(FILES[f] + str(rank))
            out.append((f'{color}{kind}_{FILES[f]}{rank}', kind, color, x, y))
    for side in ('w', 'b'):
        x, y = g.zone_xy(side, 0)
        out.append((f'{side}Q_yedek', 'Q', side, x, y))
    return out
