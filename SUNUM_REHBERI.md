# Canlı sunum — başlatma ve sınırlar

Sunum sitesi: https://mervetzll.github.io/satranc-robot/

1. Yeni bir Ubuntu terminali açın. Temiz başlatıcı yalnızca bu kullanıcıya ait satranç projesi ROS/Gazebo süreçlerini ve onların alt süreçlerini kapatır; dosya veya kilit silmez.
2. Ubuntu'da bu geliştirme klasöründeki `SUNUM_TEMIZ_BASLAT.sh` betiğini çalıştırın.
3. Betik resmi Cloudflare deposundan geçici tünel aracını gerekiyorsa indirir. Ardından ROS paketini derler; ayrı ROS domain 87 ve oturuma özel Gazebo partition ile yeni dünyayı açar. Önceki dünyayı kullanmaz.
4. Terminalde SUNUM ANAHTARI ve HOCAYA GÖNDERİLECEK CANLI SUNUM BAĞLANTISI çıkar. Bağlantı ayrıca `SUNUM_BAGLANTISI.txt` içine kaydedilir. Anahtar bu paylaşım dosyasına veya sunum sitesine yazılmaz.
5. Paylaşım bağlantısını açıp sunum anahtarını girin. ROS'a bağlan düğmesine basın. Anahtar oturum kapanınca geçersizdir; siteye kaydedilmez. Hocayla bağlantıyı ve anahtarı ayrı paylaşın.
6. Hazır durumunu bekleyin, e2e4 oynayın. Başlangıca dönmek için ROS: başlangıca dön düğmesine basıp onaylayın. Bu komut yalnızca bu yöneticinin açtığı ROS/Gazebo süreç grubunu kapatıp yeniden açar; tahta ve motor yeni oyunla başlar.
7. Sunum bilgisayarı ve bu terminal açık kalmalı. Ctrl+C, yönetilen simülasyonu, web sunucusunu ve tüneli kapatır. Geçici uzak adres yeniden başlatmada değişir; yeni bağlantıyı kullanın.

Durum: site yayımlama ve 25 yazılım testi ayrı doğrulanır. Gerçek bilgisayarda Cloudflare tüneli, GPU ile Gazebo ve sıfırlama için canlı uçtan uca deneme hâlâ gereklidir. Bu ortamdan WSL başlatılamadığı için betik kullanıcı tarafından çalıştırılmalıdır.

ROS bağlantısı veya oturum başlangıcı bekleniyorsa eski web görüntüsü doğru tahta durumu kabul edilmemelidir. ROS başlangıca dön düğmesi, eski BIRLIKTE_BASLAT/WEB_YENIDEN_BASLAT ile açılan oturumlarda kullanılamaz; SUNUM_BASLAT gerekir.

Günlükler Ubuntu'da `~/satranc_robotu_codex_ws/.sunum/` içindedir. Anahtar dosyası aynı özel dizinde 0600 izniyle tutulur ve normal kapanışta silinir. Bu dizini veya anahtarı GitHub'a yüklemeyin. Site kaynakları yalnızca `outputs/satranc-sunum-sitesi/dist` içindeki statik dosyalardır.

Denetleyiciler tek spawner ile sıralı yüklenir. Her sunum kendi ROS_HOME dizinini kullanır; eski oturumun spawner dosya kilidiyle çakışmaz. Gazebo için QT_QPA_PLATFORM=xcb seçilir. GPU hızlanması ve gerçek zaman oranı canlı oturumda ayrıca ölçülmelidir.
