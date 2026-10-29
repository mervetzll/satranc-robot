from pathlib import Path
import sys, xml.etree.ElementTree as ET
import tempfile
ROOT = Path(__file__).resolve().parents[1]
TMP = tempfile.TemporaryDirectory()
OUT = Path(TMP.name)
import xacro
root=ROOT/'ros2_ws/src/satranc_robotu'
s=(root/'urdf/satranc_robotu.urdf.xacro').read_text(encoding='utf-8').replace('$(find satranc_robotu)',root.as_posix())
tmp=OUT/'model-test.xacro';tmp.write_text(s,encoding='utf-8')
masses={}
for style in ['alu','pink']:
 for sim in ['mock','gz']:
  doc=xacro.process_file(str(tmp),mappings={'sim':sim,'style':style})
  text=doc.toxml(); e=ET.fromstring(text)
  links=e.findall('link');joints=e.findall('joint')
  assert len(links)==10 and len(joints)==9,(len(links),len(joints))
  for inertial in e.findall('link/inertial'):
   assert float(inertial.find('mass').attrib['value'])>0
   for k in ['ixx','iyy','izz']:assert float(inertial.find('inertia').attrib[k])>0
  for name in ['upper_arm','forearm']:
   link=e.find(f"link[@name='{name}']")
   assert link.find('visual/geometry') is not None and link.find('collision/geometry') is not None
  if sim=='gz':assert 'GazeboSimSystem' in text
  else:assert 'GenericSystem' in text
  masses[style]=sum(float(x.attrib['value']) for x in e.findall('link/inertial/mass'))
  (OUT/f'{style}-{sim}.urdf').write_text(text,encoding='utf-8')
  print(style,sim,len(links),'links',len(joints),'joints',round(masses[style],4),'kg')
assert masses['pink']>masses['alu']
print('4 model combinations passed')
