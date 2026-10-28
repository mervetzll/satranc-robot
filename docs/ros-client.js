/* Live ROS connection. A disconnect freezes telemetry until the user leaves ROS mode. */
(() => {
  'use strict';
  const panel = document.createElement('section');
  panel.className = 'card'; panel.style.cssText = 'padding:14px;margin:12px 0';
  panel.innerHTML = `<h2 style="margin-top:0">ROS 2 bağlantısı</h2>
    <p id="rosStatus" role="status" aria-live="polite">Tasarım modu · ROS'a bağlı değil</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
      <label for="rosUrl">Sunucu</label><input id="rosUrl" type="url" aria-label="ROS WebSocket adresi" style="flex:1;min-width:200px">
      <label for="rosKey">Sunum anahtarı</label><input id="rosKey" type="password" autocomplete="off" style="min-width:130px;max-width:220px" placeholder="Uzak bağlantı için">
      <button id="rosConnect" type="button">ROS'a bağlan</button>
      <button id="rosReset" type="button" disabled>ROS: başlangıca dön</button>
      <button id="rosLeave" type="button" disabled>Tasarım moduna dön</button>
    </div>
    <p class="note">ROS modunda kol, ROS eklem verisini izler. Taşlar son başarılı hamlenin mantıksal konumundadır; fiziksel sapmayı görmek için Gazebo'yu izleyin. Tasarım değişimi Gazebo yeniden başlatılarak yapılır. Torklar ölçüm değil model tahminidir; ROS modunda en ağır taş yükü varsayılır.</p>`;
  document.querySelector('header.top').after(panel);
  const $ = id => document.getElementById(id);
  const url = $('rosUrl'), status = $('rosStatus'), connect = $('rosConnect'), leave = $('rosLeave');
  url.value = /^https?:$/.test(location.protocol) ? `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws` : 'ws://127.0.0.1:8080/ws';
  const sharedEndpoint = new URLSearchParams(location.hash.slice(1)).get('endpoint');
  if(sharedEndpoint) { try { const u=new URL(sharedEndpoint); if(u.protocol==='wss:') url.value=u.href; } catch {} }
  let ws = null, remote = false, packet = null, lastAt = 0, session = null, lastBoard = null, pending = false;
  let configuration = null;
  const disabled = new Map();
  const controls = '#params input, #params button, #styleSeg button, #btnHome, #btnReset, #btnDemo, #tq select, #customServo input';
  function lock(on) {
    document.querySelectorAll(controls).forEach(el => {
      if(on) { if(!disabled.has(el)) disabled.set(el,el.disabled); el.disabled=true; }
      else if(disabled.has(el)) { el.disabled=disabled.get(el); }
    });
    if(!on) disabled.clear();
  }
  function fresh() { return remote && ws?.readyState === WebSocket.OPEN && Date.now()-lastAt < 3000; }
  function buttons() {
    const ready = fresh() && packet?.can_move && !pending;
    $('rosReset').disabled = !fresh() || !packet?.state_fresh;
    $('btnPlay').disabled = remote && !ready;
    $('moveInput').disabled = remote && !ready;
  }
  function message(text) { status.textContent=text; if(remote) window.SatrancROS.status(text); }
  function unavailable(text) { packet=null; buttons(); message(text); }
  function receive(event) {
    let data;
    try { data=JSON.parse(event.data); } catch { unavailable('Sunucudan geçersiz veri'); return; }
    if(data.type === 'error') { pending=false; message('Komut reddedildi: '+data.message); buttons(); return; }
    if(data.type === 'resetting') { pending=true; message('Gazebo ve ROS oyun durumu başlangıca döndürülüyor…'); buttons(); return; }
    if(data.type === 'accepted') { message(`${data.uci} ROS'a gönderildi; yürütme sonucu bekleniyor`); return; }
    if(data.type !== 'state') return;
    lastAt=Date.now(); packet=data;
    const robot=data.robot;
    if(robot && data.state_fresh) {
      const key=JSON.stringify([robot.session,robot.style,robot.geometry]);
      if(configuration !== key) {
        window.SatrancROS.configure(robot); configuration=key; session=robot.session; lastBoard=null;
      }
      const boardKey=JSON.stringify([robot.fen,robot.zone]);
      if(lastBoard !== boardKey) { window.SatrancROS.board(robot); lastBoard=boardKey; }
      if(data.telemetry_fresh) window.SatrancROS.joints(data.joints);
      if(robot.busy || robot.error || data.can_move) pending=false;
      message(`ROS · ${robot.style === 'pink' ? 'Pembe' : 'Alüminyum'} · ${data.reason || 'Hazır — beyazla hamle yapabilirsiniz'}`);
    } else message(data.reason || 'ROS verisi bekleniyor');
    buttons();
  }
  connect.addEventListener('click', () => {
    let target;
    try {
      target=new URL(url.value);
      if(!['ws:','wss:'].includes(target.protocol)) throw new Error('ws:// veya wss:// kullanın');
      if(location.protocol === 'https:' && target.protocol !== 'wss:') throw new Error('HTTPS sayfası için wss:// gerekli');
    } catch(e) { message('Bağlantı adresi geçersiz: '+e.message); return; }
    if(ws) { ws.onclose=null; ws.close(); }
    remote=true; pending=false; packet=null; configuration=null; lastBoard=null;
    window.SatrancROS.enter(); lock(true); connect.disabled=true; leave.disabled=false; url.disabled=true;
    unavailable('ROS sunucusuna bağlanılıyor…');
    try { ws=new WebSocket(target.href); } catch(e) { unavailable('Bağlantı açılamadı: '+e.message); connect.disabled=false; return; }
    const socket=ws;
    socket.onopen=() => { if($('rosKey').value) socket.send(JSON.stringify({type:'auth',key:$('rosKey').value})); };
    socket.onmessage=receive;
    socket.onclose=() => { if(socket!==ws) return; unavailable('ROS bağlantısı kesildi · son görüntü donduruldu'); connect.disabled=false; url.disabled=false; };
    socket.onerror=() => { if(socket===ws) unavailable('ROS sunucusuna erişilemiyor · Gazebo ve ağ geçidini kontrol edin'); };
  });
  $('rosReset').addEventListener('click', () => {
    if(!fresh()) return;
    if(!confirm('Gazebo dünyası ve ROS oyun durumu yeniden başlatılacak. Mevcut oyun bırakılacak. Devam edilsin mi?')) return;
    ws.send(JSON.stringify({type:'reset'})); pending=true; buttons();
  });
  leave.addEventListener('click', () => {
    remote=false;
    if(ws) { ws.onclose=null; ws.close(); ws=null; }
    packet=null; pending=false; configuration=null; lastBoard=null; $('rosKey').value='';
    lock(false); window.SatrancROS.leave(); connect.disabled=false; leave.disabled=true; url.disabled=false;
    buttons(); message('Tasarım modu · ROS bağlantısı kapatıldı. Gazebo çalışmaya devam edebilir.');
  });
  window.addEventListener('ros-move', event => {
    if(!fresh() || !packet?.can_move || pending) { message('ROS şu anda hamle kabul etmiyor'); return; }
    const uci=String(event.detail).replace(/[\s\-:x]/g,'').toLowerCase();
    if(!/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(uci)) { message('Hamleyi e2e4 biçiminde yazın'); return; }
    pending=true; buttons(); ws.send(JSON.stringify({type:'move',uci}));
    message(uci+' gönderiliyor…');
  });
  setInterval(() => {
    if(remote && lastAt && Date.now()-lastAt>3000) unavailable('ROS verisi güncellenmiyor · görüntü donduruldu');
  },500);
})();
