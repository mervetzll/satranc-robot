"""python-chess kütüphanesini PyPI'den indirip kullanıcının Python klasörüne açar (pip ve şifre gerektirmez).

Kütüphane saf Python'dur: kaynak arşivindeki 'chess' klasörünü kopyalamak kurulum için yeterlidir.
"""
import io
import json
import os
import shutil
import site
import tarfile
import tempfile
import urllib.request
import zipfile

meta = json.load(urllib.request.urlopen('https://pypi.org/pypi/chess/json'))
files = meta['urls']
pick = next((u for u in files if u['packagetype'] == 'bdist_wheel'), None) or next(u for u in files if u['packagetype'] == 'sdist')
print('indiriliyor:', pick['filename'])
data = urllib.request.urlopen(pick['url']).read()
hedef = site.getusersitepackages()
os.makedirs(hedef, exist_ok=True)
if pick['filename'].endswith('.whl'):
    zipfile.ZipFile(io.BytesIO(data)).extractall(hedef)
else:
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
            tar.extractall(tmp, filter='data')
        kok = next(os.path.join(tmp, d) for d in os.listdir(tmp))
        shutil.rmtree(os.path.join(hedef, 'chess'), ignore_errors=True)
        shutil.copytree(os.path.join(kok, 'chess'), os.path.join(hedef, 'chess'))
print('kuruldu:', hedef)
