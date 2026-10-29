#!/usr/bin/env bash
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
keyfile=Path.home()/'satranc_robotu_codex_ws'/'.sunum'/'access.key'
if not keyfile.exists():
    raise SystemExit('Açık sunum anahtarı bulunamadı. Önce SUNUM_TEMIZ_BASLAT.sh çalıştırın.')
connection=(root/'SUNUM_BAGLANTISI.txt').read_text(encoding='utf-8')
connection=connection.split('Anahtar bu dosyada')[0]
text='SATRANÇ ROBOTU — ÖZEL SUNUM NOTLARI\n\n'+connection+'\nSUNUM ANAHTARI: '+keyfile.read_text().strip()+'\n\nBağlantıyı açın. Sunucu kutusundaki adres WSS satırıyla aynı olmalı.\nSunum anahtarını girip ROS’a bağlan düğmesine basın.\nTerminal açık kalmalı. Yeniden başlatılınca bağlantı ve anahtar değişir.\nBu dosya kontrol anahtarı içerir; GitHub’a yüklemeyin.\n'
output=root/'SUNUM_OZEL_NOTLAR.txt'
output.write_text(text,encoding='utf-8-sig')
print('Özel sunum notları kaydedildi: '+str(output))
PY
