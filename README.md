# Satranç robotu — ROS ve web geliştirme sürümü

**29 Ekim 2026:** Bu klasör GitHub'daki sürümden türetilen yerel geliştirme kopyasıdır.
Yeni ROS/web bağlantısı ve pembe model eklendi. Henüz canlı Gazebo ile uçtan uca denenmedi.
Kurulum, testler ve sınırlamalar için önce [GELISTIRME.md](GELISTIRME.md) dosyasını okuyun.
`docs/` içindeki eski PDF aşağıdaki yeni özelliklerin doğrulama raporu değildir.

---

# Satranç Robotu

Satranç oynayan 5 eksenli servo kol: tasarım simülatörü, ROS 2 + Gazebo fizik simülasyonu ve
Raspberry Pi 5 üzerinde çalışacak kontrol yazılımı.

| Klasör | İçerik |
| --- | --- |
| [`web/`](web/) | Tarayıcıda çalışan tasarım simülatörü (alüminyum ve pembe tasarım, tek dosya) |
| [`ros2_ws/src/satranc_robotu/`](ros2_ws/src/satranc_robotu/) | ROS 2 paketi: URDF modeli, Gazebo dünyası, ters kinematik, hamle yürütücü, Stockfish, servo sürücü |
| [`scripts/`](scripts/) | Ubuntu (WSL2) kurulum, derleme, başlatma ve hamle gönderme betikleri |
| [`docs/`](docs/) | [Proje rehberi (PDF)](docs/satranc-robotu-rehber.pdf): tasarım, formüller, ROS 2 yapısı, test sonuçları, soru-cevap |

## Tasarım değerleri

| Değer | Seçilen |
| --- | --- |
| Kare kenarı | 5 cm (tahta 40 × 40 cm) |
| Bölmeler | Tahtanın iki yanında 4 × 4 kare (her renk için 15 yenen taş + 1 yedek vezir) |
| Taban merkezi → tahta kenarı | 9,5 cm (taban plakası yarıçapı 8,5 cm) |
| L1 omuz yüksekliği | 10 cm |
| L2 üst kol | 24 cm |
| L3 ön kol | 30 cm |
| L4 bilek → parmak ucu | 14 cm |
| Tutucu eğimi | 20° |
| Eksenler | Taban, omuz, dirsek, bilek eğimi, bilek dönüşü + paralel tutucu |
| Servolar | J1 MG996R, J2 DS3235 (35 kg), J3 DS3218 (20 kg), J4 MG996R, J5 ve tutucu MG90S |
| Denetleyici | Raspberry Pi 5 (doğrudan GPIO ya da PCA9685) |

Bu ölçüler, simülatörün hesaplarıyla 26.136 ölçü kombinasyonu taranarak seçildi: bütün karelere
çarpmadan ve servo sınırlarını aşmadan uzanan, kola %8 pay bırakan ve omuz torkunu en düşük tutan
kombinasyon. En kötü durumda omuz yaklaşık 24 kg·cm, dirsek yaklaşık 12 kg·cm ister.

## 1. Tasarım simülatörü (`web/index.html`)

Dosyayı tarayıcıda açman yeterli; kurulum gerekmez (three.js internetten yüklenir).

- 3B tahta, iki bölme ve kol; hamleyi yaz (`e2e4`) ya da kareye tıkla, siyahı robot oynar
- Satranç kuralları: rok, geçerken alma, terfi, şah, mat ve pat
- Her eklem için anlık, son hamle ve en kötü durum torku; servo kullanım oranı
- Hassasiyet (servo açı hatasının parmak ucundaki sapması), çarpışma ve taban taşma kontrolü
- Tutucu kuvveti, güç bütçesi, Raspberry Pi 5 pin planı ve hazır Python kodu
- Alüminyum ve pembe tasarım arasında tek tuşla geçiş

## 2. ROS 2 + Gazebo fizik simülasyonu

ROS 2 Lyrical ve Ubuntu 26.04 ile denendi; Windows'ta WSL2 içinde çalışır. Paketin ayrıntıları kendi
[README](ros2_ws/src/satranc_robotu/README.md) dosyasında.

```bash
bash scripts/kur_ros.sh    # ROS 2 Lyrical, Gazebo, ros2_control, Stockfish kurar ve paketi derler
bash scripts/baslat.sh     # Gazebo simülasyonunu açar
bash scripts/hamle.sh e2e4 # beyazın hamlesini gönderir; robot oynar ve Stockfish ile cevap verir
```

`kur_ros.sh` python-chess'i kuramazsa: `python3 -I scripts/chess_kur.py`.

Denenen: e2e4 ve robotun cevabı e7e5 Gazebo'da baştan sona oynandı; taşlar parmaklarla kavranıp
taşındı. Bilinen sınırlar:

- WSL2'de simülasyon gerçek zamandan yaklaşık 7 kat yavaş çalışır; bir hamle 1–2 dakika sürer.
- Kavrama sürtünmeye dayanır; taşlar hedef karenin merkezinden 6–14 mm uzağa bırakılabiliyor.
- Eklemler konum denetimiyle sürülür. Servo torkunun yetip yetmediği tarayıcı simülatöründeki tork
  hesabıyla kontrol edilir.

## 3. Gerçek robot

```bash
ros2 launch satranc_robotu real.launch.py driver:=pca   # gpio | pca | dry
```

İnsan hamlesini kendi eliyle yapar ve `/human_move` konusuna yazar (sensörden ya da elle); robot
yalnızca kendi hamlesini oynar.
