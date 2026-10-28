# satranc_robotu — ROS 2 paketi

Satranç oynayan 5 eksenli servo kolun ROS 2 paketi (Lyrical, Ubuntu 26.04; Jazzy ile de çalışacak şekilde yazıldı). Tarayıcı simülatöründe
belirlenen ölçülerle (L1 10, L2 24, L3 30, L4 14 cm, 20° tutucu eğimi, 4×4 bölme) çalışır.

- **Gazebo fizik simülasyonu:** kol, tahta ve 34 taş. Taşlar kütle ve sürtünmeyle
  modellenir; kol parmaklarıyla gerçekten kavrar ve taşır.
- **Gerçek robot:** aynı yazılım Raspberry Pi 5'te servoları sürer.

## Yapı

```
insan hamlesi ──► /human_move ──► chess_engine (Stockfish) ──► /chess_move
                        │                                         │
                        └──────────────► move_executor ◄──────────┘
                                         (ters kinematik, al-bırak planı)
                                              │  FollowJointTrajectory
                                              ▼
                              arm_controller + gripper_controller (ros2_control)
                                              │
                          ┌───────────────────┴───────────────────┐
                    Gazebo (sim:=gz)                    mock donanım (sim:=mock)
                                                               │ /joint_states
                                                               ▼
                                                     servo_driver → servolar
```

| Dosya | Görevi |
| --- | --- |
| `urdf/satranc_robotu.urdf.xacro` | Kolun ölçüleri, kütleleri, eklem sınırları (servo 0–180°) ve tork sınırları (katalog durma torku) |
| `config/controllers.yaml` | Kol ve tutucu için yörünge denetleyicileri |
| `satranc_robotu/geometry.py` | Tahta, taş ve bölme ölçüleri, ters kinematik, servo açısı eşlemesi |
| `satranc_robotu/move_executor.py` | UCI hamlesini al-bırak hareketine çevirir; yeme, rok, geçerken alma, terfi |
| `satranc_robotu/chess_engine_node.py` | İnsan hamlesini denetler, Stockfish ile robotun hamlesini seçer |
| `satranc_robotu/servo_driver_node.py` | Eklem açılarını servo açılarına çevirip GPIO ya da PCA9685 ile sürer |
| `satranc_robotu/world_models.py` | Gazebo için tahta ve taş modelleri |
| `launch/gazebo.launch.py` | Fizik simülasyonu |
| `launch/display.launch.py` | Yalnızca RViz, eklemleri kaydırma çubuğuyla oynatma |
| `launch/real.launch.py` | Gerçek robot |

## Kurulum (Ubuntu 26.04 + ROS 2 Lyrical)

ROS deposu eklendikten sonra ([resmi kurulum sayfası](https://docs.ros.org/en/lyrical/Get-Started/Installation/Ubuntu-Install-Debs.html)):

```bash
sudo apt install ros-lyrical-desktop ros-dev-tools ros-lyrical-ros-gz ros-lyrical-gz-ros2-control \
  ros-lyrical-ros2-control ros-lyrical-ros2-controllers ros-lyrical-xacro \
  ros-lyrical-joint-state-publisher-gui stockfish python3-chess
cd ~/satranc_robotu_ws
colcon build --symlink-install
source install/setup.bash
```

## Çalıştırma

Fizik simülasyonu:

```bash
ros2 launch satranc_robotu gazebo.launch.py
```

Başka bir terminalde beyazla hamle yap; robot önce senin hamleni, sonra kendi cevabını oynar:

```bash
ros2 topic pub --once -w 2 /human_move std_msgs/String "{data: e2e4}"
```

Robotun ne yaptığını izlemek için:

```bash
ros2 topic echo /robot_status
```

Yalnızca modeli görmek için:

```bash
ros2 launch satranc_robotu display.launch.py
```

Gerçek robot (Raspberry Pi 5; `driver` = `gpio`, `pca` ya da `dry`):

```bash
ros2 launch satranc_robotu real.launch.py driver:=pca
```

Gerçek tahtada insan hamlesini kendi eliyle yapar; robot yalnızca kendi hamlesini oynar.
İnsan hamlesi sensörden ya da elle `/human_move` konusuna yazılır.

## Bilinen sınırlar

- Bu paket Windows'ta hazırlandı; ROS kurulu bir bilgisayarda henüz derlenip denenmedi.
  İlk çalıştırmada küçük düzeltmeler gerekebilir.
- Gazebo'da eklemler konum denetimiyle sürülür: denetleyici hedef açıya ulaşmak için
  gereken kuvveti uygular. URDF'deki tork sınırları kaydedilmiştir, ama servonun
  yetmediği durumu görmek için eklemleri `effort` arayüzü ve PID denetleyicisiyle sürmek gerekir.
- Kavrama sürtünmeye dayanır. Taşlar kayarsa parmak sürtünmesini (URDF'de `mu1`, `mu2`)
  ya da sıkıştırma payını (`move_executor.py` içinde `close_w`) artır.
- Taşlar iki silindirle (taban + gövde) basitleştirilmiştir.
