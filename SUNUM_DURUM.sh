#!/usr/bin/env bash
set +u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
{
  echo '=== SUNUM ROS / GAZEBO DURUMU ==='
  date -Iseconds
  echo '=== GAZEBO GUNLUGU ==='
  tail -n 110 "$HOME/satranc_robotu_codex_ws/.sunum/gazebo.log" 2>&1
  echo '=== WEB GUNLUGU ==='
  tail -n 35 "$HOME/satranc_robotu_codex_ws/.sunum/web.log" 2>&1
  echo '=== TUNEL GUNLUGU ==='
  tail -n 12 "$HOME/satranc_robotu_codex_ws/.sunum/tunnel.log" 2>&1
  echo '=== ROS / GAZEBO ISLEMLERI ==='
  ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 18
  echo '=== BITTI ==='
} 2>&1 | tee "$ROOT/SUNUM_DURUM_RAPORU.txt"
