#!/usr/bin/env bash
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$HOME/satranc_robotu_codex_ws"
source /opt/ros/lyrical/setup.bash
if ! python3 -c 'import aiohttp, chess' 2>/dev/null; then
  echo 'Önce python3-aiohttp ve chess bağımlılıkları kurulmalı.'; exit 1
fi
RUNTIME="$WS/.sunum"
mkdir -p "$RUNTIME" "$WS/src/satranc_robotu"
chmod 700 "$RUNTIME"
if ! command -v cloudflared >/dev/null 2>&1 && [ ! -x "$RUNTIME/cloudflared" ]; then
  case "$(uname -m)" in x86_64) ARCH=amd64;; aarch64) ARCH=arm64;; *) echo 'Desteklenmeyen mimari';exit 1;; esac
  echo 'Cloudflare resmi deposundan geçici HTTPS tünel aracı indiriliyor.'
  curl --fail --location --retry 2 "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$ARCH" -o "$RUNTIME/cloudflared"
  chmod 700 "$RUNTIME/cloudflared"
fi
cp -r "$ROOT/ros2_ws/src/satranc_robotu/." "$WS/src/satranc_robotu/"
cd "$WS"
colcon build --symlink-install --packages-select satranc_robotu
source "$WS/install/setup.bash"
exec python3 "$ROOT/scripts/sunum_runner.py" "${1:-pink}"
