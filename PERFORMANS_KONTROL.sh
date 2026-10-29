#!/usr/bin/env bash
# Read-only diagnostics. Does not stop or reconfigure ROS/Gazebo.
set +u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT="$ROOT/PERFORMANS_RAPORU.txt"
{
  echo '=== ROS / GAZEBO PERFORMANS RAPORU ==='
  date -Iseconds
  echo '=== WSL / DONANIM ==='
  uname -r
  nproc
  free -h
  echo '=== GRAFIK ORTAMI ==='
  for key in DISPLAY WAYLAND_DISPLAY LIBGL_ALWAYS_SOFTWARE MESA_LOADER_DRIVER_OVERRIDE GALLIUM_DRIVER; do
    printf '%s=' "$key"; printenv "$key" || true
  done
  if command -v glxinfo >/dev/null 2>&1; then
    timeout 8 glxinfo -B 2>&1
  else
    echo 'glxinfo kurulu değil; Gazebo günlükleri incelenecek.'
  fi
  echo '=== GAZEBO RENDERER KAYITLARI ==='
  for file in "$HOME/.gz/rendering/ogre2.log" "$HOME/.gz/rendering/ogre.log" "$HOME/.ignition/rendering/ogre2.log"; do
    if [ -f "$file" ]; then
      echo "$file"
      grep -Ei 'GL_RENDERER|GL_VENDOR|GL_VERSION|rendering device|renderer|llvmpipe|D3D12|Direct3D|OpenGL|Mesa|Vulkan|adapter' "$file" | tail -n 40
    fi
  done
  echo '=== EN YÜKSEK CPU KULLANAN İŞLEMLER ==='
  ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 18
  echo '=== SIMULASYON ISTATISTIKLERI (5 sn) ==='
  export GZ_PARTITION=satranc_codex_test
  export ROS_DOMAIN_ID=42
  if [ -f /opt/ros/lyrical/setup.bash ]; then source /opt/ros/lyrical/setup.bash; fi
  timeout 5 gz topic -e -t /world/default/stats 2>&1 | head -n 65
  echo '=== SON GAZEBO HATALARI ==='
  if [ -f "$HOME/satranc_robotu_codex_ws/test-logs/gazebo.log" ]; then
    grep -Ei 'error|warn|real.time|render|software|physics|update.*rate' "$HOME/satranc_robotu_codex_ws/test-logs/gazebo.log" | tail -n 25
  fi
  echo '=== BITTI ==='
} 2>&1 | tee "$REPORT"
echo "Rapor kaydedildi: $REPORT"
