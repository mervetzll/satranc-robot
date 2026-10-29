#!/usr/bin/env bash
set +u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v glxinfo >/dev/null 2>&1; then
  echo 'OpenGL tanılama aracı mesa-utils kurulacak; Ubuntu şifreniz istenebilir.'
  sudo apt install -y mesa-utils || exit 1
fi
{
  echo '=== GPU KONTROLU ==='
  date -Iseconds
  echo '=== WSL GPU AYGITI ==='
  ls -l /dev/dxg /usr/lib/x86_64-linux-gnu/dri/d3d12_dri.so /usr/lib/wsl/lib/libd3d12.so /usr/lib/wsl/lib/libdxcore.so 2>&1
  echo '=== VARSAYILAN OPENGL ==='
  timeout 10 glxinfo -B 2>&1
  echo '=== YALNIZCA BU TEST ICIN D3D12 ==='
  timeout 10 env GALLIUM_DRIVER=d3d12 glxinfo -B 2>&1
  echo '=== BITTI ==='
} | tee "$ROOT/GPU_RAPORU.txt"
echo "Rapor kaydedildi: $ROOT/GPU_RAPORU.txt"
