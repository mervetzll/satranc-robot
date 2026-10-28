#!/usr/bin/env bash
# ROS 2 Lyrical + Gazebo kurulumu (Ubuntu 26.04, WSL2) ve satranc_robotu paketinin derlenmesi.
# Adımlar docs.ros.org/en/lyrical/Get-Started/Installation/Ubuntu-Install-Debs.html sayfasından.
set -e
BURASI="$(cd "$(dirname "$0")" && pwd)"
adim() { echo; echo "===== $1 ====="; }

adim "1/7 Dil ayarı (UTF-8)"
sudo apt update
sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

adim "2/7 ROS 2 deposu"
sudo apt install -y software-properties-common curl
sudo add-apt-repository -y universe
ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb

adim "3/7 Sistem güncellemesi"
sudo apt update
sudo apt upgrade -y

adim "4/7 ROS 2 Lyrical masaüstü + geliştirme araçları (birkaç GB indirir)"
sudo apt install -y ros-lyrical-desktop ros-dev-tools

adim "5/7 Gazebo, ros2_control ve satranç paketleri"
EKSIK=""
for p in ros-lyrical-ros-gz ros-lyrical-gz-ros2-control ros-lyrical-ros2-control ros-lyrical-ros2-controllers \
         ros-lyrical-xacro ros-lyrical-joint-state-publisher-gui stockfish python3-chess; do
  if sudo apt install -y "$p"; then echo "kuruldu: $p"; else EKSIK="$EKSIK $p"; fi
done
if echo "$EKSIK" | grep -q python3-chess; then
  pip install chess --break-system-packages && EKSIK="${EKSIK/python3-chess/}"
fi

adim "6/7 satranc_robotu paketini derle"
mkdir -p ~/satranc_robotu_ws/src
rm -rf ~/satranc_robotu_ws/src/satranc_robotu
cp -r "$BURASI/../ros2_ws/src/satranc_robotu" ~/satranc_robotu_ws/src/
source /opt/ros/lyrical/setup.bash
cd ~/satranc_robotu_ws
colcon build --symlink-install

adim "7/7 Her yeni terminalde ROS'u otomatik yükle"
grep -q "/opt/ros/lyrical/setup.bash" ~/.bashrc || echo "source /opt/ros/lyrical/setup.bash" >> ~/.bashrc
grep -q "satranc_robotu_ws/install/setup.bash" ~/.bashrc || echo "source ~/satranc_robotu_ws/install/setup.bash" >> ~/.bashrc

echo
if [ -n "${EKSIK// /}" ]; then
  echo "UYARI: şu paketler kurulamadı:$EKSIK"
else
  echo "Bütün paketler kuruldu."
fi
echo "KURULUM BİTTİ. Simülasyonu başlatmak için yeni bir Ubuntu terminalinde:"
echo "  ros2 launch satranc_robotu gazebo.launch.py"
