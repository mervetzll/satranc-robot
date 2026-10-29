# ROS 2, iki tasarım ve site bağlantısı — geliştirme sürümü

Bu kopya 29 Ekim 2026 tarihli geliştirmedir. GitHub'daki ana depo veya Google Sites yayını bu çalışma sırasında değiştirilmedi.

## Eklenenler
- `style:=alu` ve `style:=pink` seçenekleri: Gazebo ve RViz model açılışında seçilir.
- Pembe varyant: kalın kutu üst kol, silindirik ön kol, omuz gövdesi, pembe malzeme; eşleşen basitleştirilmiş çarpışma şekilleri ve daha yüksek kütle. Eklem eksenleri/uzunlukları aynı; aynı ters kinematik kullanılır.
- Pembe kol için malzeme+kablo 0,66 kg/m, tutucu+servo 0,0734 kg; alüminyum için 0,31 kg/m ve 0,0484 kg. Bunlar ölçülmüş değerler değil, önceki web simülatörünün varsayımlarıdır. Pembe model üretim CAD'i değildir; ön kol ataleti kutu zarfıyla yaklaşık hesaplanır. Gazebo ile web görselleri birebir CAD eşlemesi sayılmaz.
- WebSocket ağ geçidi: yalnızca yasal beyaz hamleleri `/human_move` konusuna gönderir. `/robot_state` ve `/joint_states` verisini tarayıcıya iletir; keyfi konu yayınlama veya terminal komutu çalıştırma sunmaz.
- ROS modunda tarayıcı kendi motorunu/animasyonunu çalıştırmaz. Robotun stili ve geometrisi ROS'tan gelir. Model değiştirmek Gazebo'nun yeniden başlatılmasını gerektirir; sayfadaki stil düğmeleri bağlantı sırasında kilitlidir.
- Taşlar son başarılı hareketten sonraki **mantıksal** FEN durumuyla çizilir. Gazebo'daki taşın gerçek konumu, kayması veya düşmesi web tarafında henüz ölçülmez. Eklem açıları ROS verisidir; torklar hâlâ model tahminidir. ROS modunda yük için en ağır taş varsayılır.
- Bağlantı/eski veri durumunda hareket düğmesi kapanır; görüntü donar. Otomatik komut tekrarı yapılmaz. İki istemcinin eşzamanlı yeni hamle göndermesi kapı katmanında engellenir.
- Hamle başarısızsa `/move_done` yayınlanmaz, doğrulanmış tahta ilerlemez ve yeni hareketler durur. Motor, karşı hamleyi insan hamlesinin başarılı tamamlanmasından sonra seçer. Zaman aşımında yörünge iptali istenir; otomatik kurtarma hareketi yapılmaz. İptalin fiziksel tamamlanması ayrıca doğrulanmalıdır.

## Ubuntu'da ilk canlı deneme

Önce eski Claude/Gazebo çalışmasını bitirin. Mevcut çalışma alanınızın kopyasını saklayın. Aşağıdaki komutlar bu geliştirme klasörünün **Ubuntu'dan görülen kökünde** çalıştırılır. Eski Linux kaynak klasörünü silmek yerine ROS paketi ek dosyalarıyla üzerine kopyalanır; kalmış eski dosyalar varsa ayrıca incelenmelidir.

```bash
sudo apt install python3-aiohttp
mkdir -p ~/satranc_robotu_ws/src/satranc_robotu
cp -r ros2_ws/src/satranc_robotu/. ~/satranc_robotu_ws/src/satranc_robotu/
source /opt/ros/lyrical/setup.bash
cd ~/satranc_robotu_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch satranc_robotu gazebo.launch.py style:=pink
```

Alüminyum için son komutta `style:=alu` kullanın. Yalnızca RViz modeli için `ros2 launch satranc_robotu display.launch.py style:=pink` çalıştırılabilir; bu fizik testi değildir.

İkinci Ubuntu terminalinde geliştirme klasörünün köküne dönüp:

```bash
bash scripts/web_baslat.sh
```

Tarayıcıda `http://localhost:8080/` açın. Siteyi ve WebSocket'i aynı ağ geçidi sunar. Sunucu alanı `ws://localhost:8080/ws` olmalı; **ROS'a bağlan** düğmesine basın. Kontrol düğümleri hazır ve eklem verisi güncelse Oynat açılır. `e2e4` girin. Durum, kol açıları ve başarılı hareketlerden sonraki tahta değişimini izleyin.

Windows'ta localhost yönlendirmesi WSL ayarlarına bağlıdır. Sayfa açılmazsa önce Ubuntu içindeki `curl http://127.0.0.1:8080/` sonucunu kontrol edin. Ağ geçidi varsayılan olarak yalnızca loopback adresinde dinler.

## Canlı kabul kontrolü — henüz tamamlanmadı

1. Her modelde `/joint_states` güncellensin, 3 denetleyici etkin olsun ve başlangıç konumuna dönüş başarılı olsun.
2. Web'den e2e4 bir kez gönderilsin. Motor, beyazın hareketi bitmeden siyah hareketini göndermesin; sonra e7e5 veya seçtiği başka yasal hamle yürüsün.
3. Gazebo'da taşların yerleri fiziksel olarak incelensin. Önceki testteki 6–14 mm sapma bu sürümde giderilmiş kabul edilmez.
4. Başka tarayıcıdan aynı anda hamle gönderildiğinde ikinci komut reddedilsin. WebSocket kapanınca veya ROS durunca site hareket göndermesin.
5. Denetleyici hatasında başarı mesajı oluşmasın. Robotun konumu bilinmiyorsa sistemi/tahtayı sıfırlamadan yeni oyun başlatmayın.
6. Rok, yeme, geçerken alma ve terfi ayrı fizik testleriyle doğrulansın.

## Çevrim içi gösterim

GitHub Pages veya Google Sites tek başına ROS/Gazebo çalıştırmaz. Simülasyonu çalıştıran bilgisayar açık kalmalıdır. Uzaktan gösterim için bu HTTP/WebSocket servisine HTTPS/WSS sağlayan, erişim denetimi olan bir ters vekil/tünel kurulmalıdır. Bu çalışmada tünel veya herkese açık yayın açılmadı.

En basit gösterim, ağ geçidinin sunduğu sitenin erişim denetimli HTTPS adresini açmaktır; sayfa aynı sunucudaki WSS adresini kullanır. Ayrı bir web alanından bağlanılacaksa ağ geçidine `-p allowed_origin:=https://TAM-ALAN-ADI` verilir. Joker origin yoktur. Google Sites'a sadece HTML yapıştırmak yeterli değildir; `ros-client.js` de aynı site kaynağından sunulmalıdır. Google Sites'a bütün çalışan arayüzün HTTPS adresi gömülebilir; iframe/oturum ve erişim denetimi ayrıca test edilmelidir.

## Doğrulama

Windows üzerinde:
- Alüminyum/pembe × mock/Gazebo olmak üzere dört Xacro açılımı yapıldı: her biri 10 bağlantı ve 9 eklem; pozitif kütle/atalet ve donanım eklentileri kontrol edildi.
- 9 komut kapısı testi ve 8 yürütücü/motor/WebSocket testi geçti. Entegrasyon testleri ROS adaptörlerini taklit eder, gerçek ROS çalışması değildir.
- JavaScript ve Python sözdizimi kontrolleri geçti.
- Tarayıcıda pembe tasarıma geçiş, bağlantısızken hareket engeli ve ayrı, açıkça etiketli test verisiyle eklem aktarımı kontrol edildi. Bu test verisi ürüne dahil edilmedi.
- Bu ortamdan WSL çağrısı `Wsl/E_ACCESSDENIED` döndüğü için gerçek ROS/Gazebo derlemesi ve tam hamle testi **yapılamadı**.

Testleri ROS gerektirmeden tekrar çalıştırmak için Python ortamında:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/check_models.py
```

Kaynak başvuruları: [aiohttp WebSocket/HTTP](https://docs.aiohttp.org/en/stable/web_quickstart.html), [ROS yörünge denetleyicisi](https://control.ros.org/rolling/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html).


## Bu bilgisayarda GPU kontrolü
GPU_RAPORU.txt içinde varsayılan OpenGL llvmpipe/Accelerated:no, GALLIUM_DRIVER=d3d12 testinde Intel UHD/Accelerated:yes görüldü. Başlatma betikleri D3D12 ortamını seçer; bu bilgisayara özgü ayardır. RViz varsayılan olarak kapalıdır, rviz:=true ile açılır. Gazebo yeniden başlatıldıktan sonra yeni ogre2.log ve RTF ölçümüyle hızlanma ayrıca doğrulanmalıdır.
