'use strict';
const $=id=>document.getElementById(id);
const csrf=document.querySelector('meta[name="csrf-token"]').content;
const pages={
 overview:{label:'Übersicht',icon:'grid',description:'Deine Telefonie. Ein klarer Platz für jeden Teil.'},
 accounts:{label:'SIP-Zugänge',icon:'shield',description:'Anbieter, Server und Zugangsdaten deiner Telefonanschlüsse.'},
 numbers:{label:'Rufnummern',icon:'phone',description:'Rufnummern zuordnen und festlegen, wo eingehende Anrufe klingeln.'},
 devices:{label:'Kiosks & Geräte',icon:'devices',description:'Jedes Gerät mit eigener Nebenstelle und eigenen Verbindungsdaten.'},
 contacts:{label:'Kontakte',icon:'users',description:'Das Telefonbuch für die Web-Telefonseite.'},
 network:{label:'Netzwerk',icon:'network',description:'Adressen, Ports und Zugriff für dieses Telefoniesystem.'},
 diagnostics:{label:'Diagnose',icon:'pulse',description:'Verbindungsstatus und Konfiguration an einem Ort.'}
};
const paths={
 grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
 shield:'M12 3l8 3v6c0 5-8 9-8 9S4 17 4 12V6z M8 12l3 3 5-6',
 phone:'M6 3l4 1-1 5c2 3 3 4 6 6l5-1 1 4c-1 4-5 3-8 1C7 16 3 12 3 7c0-2 1-3 3-4z',
 devices:'M7 3h10v18H7z M11 18h2 M3 8v8 M21 8v8',
 users:'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M2 21v-3c0-5 14-5 14 0v3 M17 4c5 0 5 7 0 7 M19 15c3 0 3 3 3 6',
 network:'M8 3h8v6H8z M3 17h6v4H3z M15 17h6v4h-6z M12 9v4 M6 17v-4h12v4',
 pulse:'M2 12h5l3-8 4 16 3-8h5',
 plus:'M12 5v14 M5 12h14',
 arrow:'M5 12h14 M14 7l5 5-5 5',
 check:'M5 12l4 4L19 6',
 edit:'M4 20l4-1L20 7l-3-3L5 16z M14 7l3 3',
 trash:'M4 7h16 M9 3h6l1 4 M6 7l1 14h10l1-14 M10 11v6 M14 11v6',
 export:'M12 16V3 M7 8l5-5 5 5 M4 15v6h16v-6',
 server:'M3 4h18v6H3z M3 14h18v6H3z M7 7h1 M7 17h1 M16 7h2 M16 17h2',
 info:'M12 8h.01 M12 11v6 M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z',
 star:'M12 3l3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z'
};
function icon(name){return '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="'+(paths[name]||paths.grid)+'"/></svg>';}
function e(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function uid(prefix){return prefix+Date.now().toString(36)+Math.random().toString(36).slice(2,6);}
function badge(label,kind=''){return '<span class="badge '+kind+'"><span class="badge-dot"></span>'+e(label)+'</span>';}
function action(label,kind,id,extra=''){return '<button class="button '+extra+'" data-action="'+kind+'" data-id="'+e(id||'')+'">'+e(label)+'</button>';}
function addButton(label,kind){return '<button class="button primary" data-action="add-'+kind+'">'+icon('plus')+e(label)+'</button>';}
function editButton(kind,id){return '<button class="icon-button" aria-label="Bearbeiten" data-action="edit-'+kind+'" data-id="'+e(id)+'">'+icon('edit')+'</button>';}
function deleteButton(kind,id){return '<button class="icon-button danger" aria-label="Entfernen" data-action="delete-'+kind+'" data-id="'+e(id)+'">'+icon('trash')+'</button>';}
function row(label,value){return '<div class="key-value"><span>'+e(label)+'</span><strong>'+e(value)+'</strong></div>';}
function tile(name,cls=''){return '<span class="icon-tile '+cls+'">'+icon(name)+'</span>';}
function field(name,label,value='',opt={}){
 let input='';
 const attrs=' name="'+e(name)+'" id="f_'+e(name)+'" aria-label="'+e(label)+'"'+(opt.required?' required':'')+(opt.max?' maxlength="'+opt.max+'"':'')+(opt.minLength?' minlength="'+opt.minLength+'"':'')+(opt.readonly?' readonly':'')+(opt.placeholder?' placeholder="'+e(opt.placeholder)+'"':'');
 if(opt.options)input='<select'+attrs+'>'+opt.options.map(o=>'<option value="'+e(o.value)+'"'+(String(value)===String(o.value)?' selected':'')+(o.disabled?' disabled':'')+'>'+e(o.label)+'</option>').join('')+'</select>';
 else if(opt.type==='textarea')input='<textarea'+attrs+' rows="3">'+e(value)+'</textarea>';
 else input='<input type="'+(opt.type||'text')+'"'+attrs+(opt.type==='password'?' autocomplete="new-password"':'')+(opt.type==='number'?' min="'+(opt.min||1024)+'" max="'+(opt.maxNumber||65535)+'"':'')+' value="'+e(value)+'">';
 return '<label class="form-field'+(opt.full?' full':'')+'">'+e(label)+input+(opt.help?'<span class="form-help">'+e(opt.help)+'</span>':'')+'</label>';
}
function switchField(name,label,checked,help=''){return '<label class="switch-row"><span><strong>'+e(label)+'</strong><small>'+e(help)+'</small></span><input type="checkbox" name="'+e(name)+'" aria-label="'+e(label)+'"'+(checked?' checked':'')+'></label>';}
function empty(title,description,kind,label){return '<div class="card empty-state">'+tile(pages[kind]?.icon||'phone')+'<h2>'+e(title)+'</h2><p>'+e(description)+'</p>'+addButton(label,kind)+'</div>';}
let state=null,draft=null,providers={},live={},page='overview',busy=false,editor=null,previousFocus=null,formDirty=false,toastTimer;
async function api(path,body){
 const options=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(body)};
 const response=await fetch(path,options);
 let data;try{data=await response.json();}catch{throw new Error('Die Antwort konnte nicht gelesen werden. Seite neu laden.');}
 if(!response.ok||data.ok===false)throw new Error(data.error||'Anfrage fehlgeschlagen.');
 return data;
}
function toast(message,error=false){clearTimeout(toastTimer);$('toast').textContent=message;$('toast').className='toast'+(error?' error':'');$('toast').hidden=false;$('toast').setAttribute('role',error?'alert':'status');toastTimer=setTimeout(()=>$('toast').hidden=true,error?10000:5000);}
function clean(value){return JSON.parse(JSON.stringify(value),(key,item)=>key.endsWith('_set')?undefined:item);}
function adopt(data){state={...state,...data};draft=data.draft;if(data.status)live=data.status;formDirty=false;render();}
async function save(next){if(busy)return false;busy=true;setBusy();try{adopt(await api('api/setup/workspace',{draft:clean(next),revision:state.revision}));toast('Entwurf gespeichert. Anwenden übernimmt die Änderungen.');return true;}catch(error){toast(error.message,true);return false;}finally{busy=false;setBusy();}}
function setBusy(){$('applyButton').disabled=busy||!state;$('saveEntity').disabled=busy;}
function account(id){return draft.connections.find(c=>c.id===id);}
function numberStatus(n){const c=account(n.connection_id);if(!c?.enabled)return badge('Deaktiviert');if(!live.asterisk_running)return badge('Noch nicht aktiv');const s=(live.lines||[]).find(l=>l.id===n.id);return s?.registered?badge('Registriert','good'):badge(s?.state==='abgelehnt'?'Abgelehnt':'Wartet','warn');}
function connectionStatus(c){const n=draft.numbers.find(n=>n.connection_id===c.id);return n?numberStatus(n):badge('Nicht zugeordnet');}
function deviceStatus(d){if(!d.enabled)return badge('Deaktiviert');if(!live.asterisk_running)return badge('Noch nicht aktiv');return (live.devices||[]).some(s=>s.extension===d.extension&&s.registered)?badge('Verbunden','good'):badge('Nicht angemeldet','warn');}
function targetNames(n){if(!n.incoming_devices.length)return ['Alle aktiven Kiosks'];return n.incoming_devices.map(ext=>draft.devices.find(d=>d.extension===ext)?.name||(ext==='100'?'Telefon 100':ext));}
function renderNav(){
 $('navigation').innerHTML=Object.entries(pages).map(([key,p],i)=>(i===5?'<div class="nav-divider"></div>':'')+'<a class="nav-link'+(page===key?' active':'')+'" href="#'+key+'"'+(page===key?' aria-current="page"':'')+'>'+icon(p.icon)+'<span>'+p.label+'</span>'+(key==='accounts'?'<span class="nav-count">'+draft.connections.length+'</span>':key==='devices'?'<span class="nav-count">'+draft.devices.length+'</span>':'')+'</a>').join('');
}
function renderBar(){
 const pending=state.applied.revision!==state.revision;
 $('saveDot').className='save-dot'+(pending?' pending':'');
 $('saveState').textContent=pending?'Entwurf gespeichert · noch nicht angewendet':'Konfiguration übernommen';
 $('applyHint').textContent=draft.demo?'Beispieldaten · kein echter Telefonbetrieb':draft.runtime_enabled?'Anwenden startet den Telefonserver mit dem gespeicherten Entwurf neu.':'Telefonserver ausgeschaltet.';
 $('applyButton').innerHTML=(pending?'Änderungen anwenden':'Erneut anwenden')+' <span aria-hidden="true">↗</span>';
}
function render(){
 if(!draft)return;
 renderNav();renderBar();
 const p=pages[page];$('pageTitle').textContent=p.label;$('pageDescription').textContent=p.description;
 $('eyebrow').textContent=page==='overview'?'DEIN TELEFONIE-WORKSPACE':'TELEFONIE / '+p.label.toUpperCase();
 $('sampleBanner').innerHTML=draft.demo?'<div class="notice sample">'+icon('info')+'<div><strong>Du siehst Beispieldaten.</strong><p>Erkunde die Struktur. Diese Daten werden nicht für Anrufe oder Registrierungen verwendet.</p></div>'+action('Eigene Konfiguration starten','reset-blank','','quiet')+'</div>':'';
 $('pageActions').innerHTML=({overview:(!draft.connections.length&&!draft.devices.length&&!draft.runtime_enabled? action('Beispieldaten ansehen','reset-sample','','secondary'):''),accounts:addButton('SIP-Zugang hinzufügen','accounts'),numbers:addButton('Rufnummer hinzufügen','numbers'),devices:addButton('Kiosk hinzufügen','devices'),contacts:addButton('Kontakt hinzufügen','contacts'),network:'',diagnostics:action('Status aktualisieren','refresh','','secondary')})[page];
 $('pageContent').innerHTML=({overview:overview,accounts:accountsPage,numbers:numbersPage,devices:devicesPage,contacts:contactsPage,network:networkPage,diagnostics:diagnosticsPage})[page]();
}
function overview(){
 const connected=draft.devices.filter(d=>(live.devices||[]).some(s=>s.extension===d.extension&&s.registered)).length;
 const stats=[['SIP-Zugänge',draft.connections.length,'accounts','shield','Anbieter & Anmeldedaten'],['Rufnummern',draft.numbers.length,'numbers','phone','Eingehend & ausgehend'],['Kiosks & Geräte',draft.devices.length,'devices','devices',connected+' aktuell verbunden']];
 const steps=[['accounts','SIP-Zugang anlegen','Dein Anbieter und seine Zugangsdaten.',draft.connections.length>0],['numbers','Rufnummer zuordnen','Ein Anschluss, eine Rufnummer und ihre Klingelziele.',draft.numbers.length>0],['devices','Kiosks verbinden','Eine eigene Nebenstelle für jedes Gerät.',draft.devices.length>0||draft.audio.phone_password_set],['network','Netzwerk festlegen','Server-Adresse und getrennte SIP-Ports.',!!draft.network.listen_address]];
 const done=steps.filter(s=>s[3]).length;
 return '<div class="stats-grid">'+stats.map((s,i)=>'<a class="card stat-card" href="#'+s[2]+'"><div><div class="stat-label">'+s[0]+'</div><div class="stat-number">'+s[1]+'</div><div class="stat-footer">'+s[4]+'</div></div>'+tile(s[3],i===1?'blue':i===2?'amber':'')+'</a>').join('')+'</div>'+
 '<div class="dashboard-grid"><div class="stack"><section class="card"><div class="card-header"><div><h2>Alles bereit für deinen Anschluss?</h2><p class="muted">Vier Bausteine, klar voneinander getrennt.</p></div>'+badge(done+' / 4',done===4?'good':'')+'</div><div class="card-body"><div class="setup-progress"><span class="progress-'+done+'"></span></div>'+steps.map((s,i)=>'<div class="check-row"><span class="check-step'+(s[3]?' done':'')+'">'+(s[3]?icon('check'):i+1)+'</span><div><h3>'+s[1]+'</h3><p>'+s[2]+'</p></div><a class="text-link" href="#'+s[0]+'">'+(s[3]?'Öffnen':'Einrichten')+icon('arrow')+'</a></div>').join('')+'</div></section>'+
 '<section class="card"><div class="card-header"><div><h2>So hängen die Bereiche zusammen</h2><p class="muted">Zugangsdaten bleiben beim Anschluss. Klingelziele bei der Rufnummer.</p></div></div><div class="card-body"><div class="flow"><div class="flow-node">'+tile('shield')+'SIP-Zugang<small>Anmeldung beim Anbieter</small></div><span class="flow-arrow">→</span><div class="flow-node">'+tile('phone','blue')+'Rufnummer<small>Nummer & Anrufregeln</small></div><span class="flow-arrow">→</span><div class="flow-node">'+tile('devices','amber')+'Kiosks<small>Mikrofon & Lautsprecher</small></div></div></div></section></div>'+
 '<div class="stack"><section class="card"><div class="card-header"><h2>Telefonserver</h2>'+badge(live.asterisk_running?'Aktiv':'Ausgeschaltet',live.asterisk_running?'good':'')+'</div><div class="card-body"><div class="server-state"><span class="server-indicator">'+icon('server')+'</span><div><strong>'+(live.asterisk_running?'Bereit für Verbindungen':'Noch kein Telefonbetrieb')+'</strong><p class="muted">'+(live.asterisk_running?'Asterisk stellt die Telefonverbindungen bereit.':'Entwürfe können bereits bearbeitet werden.')+'</p></div></div>'+row('SIP-Adresse',(draft.network.listen_address||'Noch nicht festgelegt')+':'+draft.network.sip_port)+row('RTP-Bereich','30000–30100 / UDP')+row('Konfiguration','Entwurf '+state.revision)+'<p class="inline-info">Die gespeicherten Anschlüsse und Geräte werden von diesem Gateway verwaltet.</p><a class="text-link" href="#network">Server-Einstellungen '+icon('arrow')+'</a></div></section>'+
 '<section class="card"><div class="card-header"><h2>Deine Rufnummern</h2><a class="text-link" href="#numbers">Alle '+icon('arrow')+'</a></div><div class="card-body">'+(draft.numbers.length?draft.numbers.slice(0,3).map(n=>'<div class="key-value"><div><strong>'+e(n.name)+'</strong><div class="muted small">'+e(n.number)+'</div></div>'+numberStatus(n)+'</div>').join(''):'<p class="empty-inline">Noch keine Rufnummer angelegt.</p>')+'</div></section></div></div>';
}
function accountsPage(){
 if(!draft.connections.length)return empty('Dein Anschluss beginnt hier.','Lege deinen SIP-Zugang an. Rufnummern und Kiosks ordnest du anschließend in ihren eigenen Bereichen zu.','accounts','SIP-Zugang hinzufügen');
 return '<div class="content-toolbar"><p class="muted">'+draft.connections.length+' Zugang'+(draft.connections.length===1?'':'e')+' · Passwörter werden nach dem Speichern nicht angezeigt.</p></div><div class="record-grid">'+draft.connections.map(c=>'<article class="card record-card"><div class="record-top">'+tile('shield')+'<div><span class="record-title">'+e(c.name)+'</span><div class="record-subtitle">'+e(providers[c.provider]?.name||c.provider)+'</div></div>'+connectionStatus(c)+'</div><div class="record-details"><div><span>Registrar</span><strong>'+e(c.registrar||providers[c.provider]?.registrar||'Noch nicht festgelegt')+'</strong></div><div><span>Anmeldung</span><strong>'+e(c.auth_mode==='access'?'Anschlussbasiert':c.auth_username||'Noch nicht festgelegt')+'</strong></div><div><span>Rufnummer</span><strong>'+e(draft.numbers.find(n=>n.connection_id===c.id)?.number||'Nicht zugeordnet')+'</strong></div></div><div class="record-footer"><span class="small muted">'+(c.auth_password_set?'Passwort gespeichert':c.auth_mode==='access'?'Ohne SIP-Passwort':'Passwort noch offen')+'</span><div class="record-actions">'+editButton('accounts',c.id)+deleteButton('accounts',c.id)+'</div></div></article>').join('')+'</div>';
}
function numbersPage(){
 if(!draft.numbers.length)return empty('Wohin soll es klingeln?','Eine Rufnummer verbindet deinen SIP-Zugang mit den passenden Kiosks. Die Zugangsdaten bleiben im Bereich SIP-Zugänge.','numbers','Rufnummer hinzufügen');
 return '<div class="content-toolbar"><p class="muted">'+draft.numbers.length+' Rufnummer'+(draft.numbers.length===1?'':'n')+'</p><label class="form-field small">Ausgehend standardmäßig<select id="outboundSelect" aria-label="Ausgehende Standardrufnummer"><option value="">Keine ausgehenden Anrufe</option>'+draft.numbers.filter(n=>n.incoming_mode==='normal').map(n=>'<option value="'+e(n.id)+'"'+(draft.outbound_number===n.id?' selected':'')+'>'+e(n.name+' · '+n.number)+'</option>').join('')+'</select></label></div><div class="card table-wrap"><table><thead><tr><th>RUFNUMMER</th><th>SIP-ZUGANG</th><th>KLINGELZIELE</th><th>STATUS</th><th><span class="muted">AKTIONEN</span></th></tr></thead><tbody>'+draft.numbers.map(n=>'<tr><td><strong>'+e(n.name)+'</strong>'+(draft.outbound_number===n.id?' <span class="badge good">Standard</span>':'')+'<small class="number-text">'+e(n.number)+'</small></td><td>'+e(account(n.connection_id)?.name||'Nicht zugeordnet')+'<small>'+e(n.incoming_mode==='announcement'?'Durchsage':n.incoming_mode==='reject'?'Anrufe abweisen':'Normale Anrufe')+'</small></td><td><div class="target-chips">'+targetNames(n).map(name=>'<span class="target-chip">'+e(name)+'</span>').join('')+'</div></td><td>'+numberStatus(n)+'</td><td><div class="record-actions">'+editButton('numbers',n.id)+deleteButton('numbers',n.id)+'</div></td></tr>').join('')+'</tbody></table></div>';
}
function devicesPage(){
 const intro='<div class="notice">'+icon('info')+'<div><strong>Eine Nebenstelle pro Kiosk.</strong><p>Im nativen KS-Plugin die Server-Adresse, den SIP-Port, die Nebenstelle und das zugehörige Gerätepasswort eintragen.</p></div></div>';
 const cards=draft.devices.length?'<div class="record-grid">'+draft.devices.map(d=>'<article class="card record-card"><div class="record-top">'+tile('devices','amber')+'<div><span class="record-title">'+e(d.name)+'</span><div class="record-subtitle">'+e(d.room||'Kein Raum zugeordnet')+'</div></div>'+deviceStatus(d)+'</div><div class="record-details"><div><span>Nebenstelle</span><strong class="mono">'+e(d.extension)+'</strong></div><div><span>Geräte-IP</span><strong>'+e(d.address||'Nicht hinterlegt')+'</strong></div><div><span>Klingelt bei</span><strong>'+e(draft.numbers.filter(n=>!n.incoming_devices.length||n.incoming_devices.includes(d.extension)).map(n=>n.name).join(', ')||'Noch keiner Rufnummer')+'</strong></div></div><div class="record-footer"><button class="text-link" data-action="connect-device" data-id="'+e(d.id)+'">Verbindungsdaten '+icon('arrow')+'</button><div class="record-actions">'+editButton('devices',d.id)+deleteButton('devices',d.id)+'</div></div></article>').join('')+'</div>':empty('Der erste Kiosk wartet.','Füge ein Tablet oder SIP-Gerät hinzu. Es erhält eine eigene Nebenstelle von 101 bis 199.','devices','Kiosk hinzufügen');
 return intro+cards+'<div class="content-toolbar extra-top"><p class="muted">Bestehende Einzelanmeldung oder Intercom-Brücke?</p>'+action('Weitere Audio-Ziele','audio-settings','','quiet')+'</div>';
}
function contactsPage(){
 if(!draft.contacts.length)return empty('Menschen statt Nummern.','Hinterlege häufige Kontakte für die Web-Telefonseite. Geräte und Nebenstellen verwaltest du unter Kiosks & Geräte.','contacts','Kontakt hinzufügen');
 return '<div class="card table-wrap"><table><thead><tr><th>KONTAKT</th><th>TELEFONNUMMER</th><th>RAUM / NOTIZ</th><th>AKTIONEN</th></tr></thead><tbody>'+draft.contacts.map(c=>'<tr><td><strong>'+e(c.name)+'</strong>'+(c.favorite?' <span class="badge good">Favorit</span>':'')+'</td><td class="number-text">'+e(c.number)+'</td><td>'+e(c.room||'—')+'</td><td><div class="record-actions">'+editButton('contacts',c.id)+deleteButton('contacts',c.id)+'</div></td></tr>').join('')+'</tbody></table></div>';
}
function networkPage(){
 const n=draft.network,w=draft.web;
 return '<form id="networkForm"><section class="card form-card"><div class="form-card-header">'+tile('network')+'<div><h2>Server & Heimnetz</h2><p class="muted">Die Adresse, unter der deine Kiosks den Telefonserver erreichen.</p></div></div><div class="form-grid">'+field('listen_address','IPv4-Adresse des HAOS-Systems',n.listen_address,{placeholder:'Eigene lokale HAOS-IP',help:'Die feste LAN-Adresse deines Home-Assistant-Systems.'})+field('local_network','Lokales Netzwerk (CIDR)',n.local_network,{placeholder:'Eigenes IPv4-Netz / Präfix',help:'Die Netzmaske aus Home Assistant oder dem Router übernehmen.'})+field('sip_port','SIP-Port des Telefonservers',n.sip_port,{type:'number',help:'Standard 5070. Einen freien Port im Heimnetz verwenden.'})+field('external_address','Öffentliche IPv4-Adresse (optional)',n.external_address,{help:'Nur eintragen, wenn die NAT-Konfiguration dies erfordert.'})+'</div>'+row('RTP-Audio','30000–30100 / UDP')+row('Lokales AMI','127.0.0.1:5038')+'</section>'+
 '<section class="card form-card"><div class="form-card-header">'+tile('server','blue')+'<div><h2>Telefonserver</h2><p class="muted">Entwurf und laufender Telefonbetrieb sind getrennt.</p></div></div>'+switchField('runtime_enabled','Telefonserver aktivieren',draft.runtime_enabled,'Wird erst mit „Änderungen anwenden“ gestartet. Eigene Zugänge und Geräte erforderlich.')+'<p class="inline-info">Anwenden übernimmt den gespeicherten Entwurf und startet den Telefonserver neu. Anbieter-Zugangsdaten bleiben zentral auf diesem Gateway.</p></section>'+
 '<section class="card form-card"><div class="form-card-header">'+tile('shield')+'<div><h2>Web-Telefonseite im LAN</h2><p class="muted">Die Verwaltung bleibt ausschließlich über Home Assistant erreichbar.</p></div></div>'+switchField('lan_enabled','Web-Telefonseite im Heimnetz erlauben',w.lan_enabled,'Erfordert einen separaten Web-Benutzer und ein Passwort.')+'<div class="form-grid">'+field('web_username','Web-Benutzername',w.web_username,{max:40})+field('web_password','Web-Passwort','',{type:'password',minLength:12,max:256,placeholder:w.web_password_set?'Gespeichert · leer lassen zum Behalten':'Mindestens zwölf Zeichen'})+'</div>'+row('Web-Port',state.gateway_port)+'<p class="inline-info">Nach einer Änderung des LAN-Zugriffs das Add-on neu starten.</p></section><div class="form-footer"><button class="button primary" type="submit">Netzwerk-Entwurf speichern</button></div></form>';
}
function diagnosticsPage(){
 const items=[['Telefonserver',live.asterisk_running?'Asterisk läuft':'Ausgeschaltet',live.asterisk_running?'good':''],...draft.connections.map(c=>{const n=draft.numbers.find(n=>n.connection_id===c.id);const s=(live.lines||[]).find(s=>s.id===n?.id);return [c.name,s?.registered?'Registriert':c.enabled?'Noch nicht registriert':'Deaktiviert',s?.registered?'good':''];}),...draft.devices.map(d=>[d.name+' · '+d.extension,(live.devices||[]).some(s=>s.extension===d.extension&&s.registered)?'Verbunden':'Nicht angemeldet',''])];
 return '<div class="dashboard-grid"><section class="card"><div class="card-header"><h2>Verbindungen</h2>'+badge('Live-Status')+'</div>'+items.map(i=>'<div class="diagnostic-row"><div><strong>'+e(i[0])+'</strong></div>'+badge(i[1],i[2])+'</div>').join('')+(live.startup_error?'<div class="diagnostic-row"><p class="danger">'+e(live.startup_error)+'</p></div>':'')+'</section><div class="stack"><section class="card"><div class="card-header"><h2>Konfiguration</h2></div><div class="card-body">'+row('Entwurf',state.revision)+row('Zuletzt angewendet',state.applied.revision<0?'Noch nicht':state.applied.revision)+row('Umgebung','SIP Phone · 26.10.17')+'<p class="inline-info">Der Export enthält keine Passwörter, Schlüssel oder PINs.</p>'+action('Konfiguration exportieren','export','','secondary')+'</div></section><section class="card"><div class="card-header"><h2>Audio testen</h2></div><div class="card-body"><p class="muted small">Bei einem angemeldeten nativen Kiosk die Nummer <strong>600</strong> wählen. Der Echo-Test bleibt im Telefonserver.</p><p class="inline-info">Die alternative Intercom-Brücke lässt sich hier prüfen, sobald sie im Telefoniesystem eingerichtet und angewendet ist.</p><div class="settings-tabs">'+action('Brücke prüfen','probe','','secondary')+action('Brücken-Echo','echo','','secondary')+'</div></div></section></div></div>';
}
function openEditor(kind,item=null){
 previousFocus=document.activeElement;editor={kind,id:item?.id||null,original:item};
 $('editorEyebrow').textContent=({accounts:'SIP-ZUGANG',numbers:'RUFNUMMER',devices:'KIOSK / GERÄT',contacts:'TELEFONBUCH',audio:'WEITERE AUDIO-ZIELE',connect:'VERBINDUNGSDATEN'})[kind];
 $('editorTitle').textContent=kind==='audio'?'Weitere Audio-Ziele':kind==='connect'?item.name:item?'Eintrag bearbeiten':({accounts:'SIP-Zugang hinzufügen',numbers:'Rufnummer hinzufügen',devices:'Kiosk hinzufügen',contacts:'Kontakt hinzufügen'})[kind];
 $('editorBody').innerHTML=({accounts:accountEditor,numbers:numberEditor,devices:deviceEditor,contacts:contactEditor,audio:audioEditor,connect:connectEditor})[kind](item||{});
 $('saveEntity').textContent=kind==='connect'?'Fertig':'Entwurf speichern';
 $('editorBackdrop').hidden=false;document.body.classList.add('modal-open');
 if(kind==='accounts')updateAuthVisibility();
 if(kind==='numbers')updateNumberVisibility();
 if(kind==='audio')updateAudioVisibility();
 const first=$('editorBody').querySelector('input:not([type=checkbox]),select,button');if(first)first.focus();
}
function closeEditor(){$('editorBackdrop').hidden=true;$('editorBody').replaceChildren();document.body.classList.remove('modal-open');editor=null;if(previousFocus?.isConnected)previousFocus.focus();else $('main').focus();}
function accountEditor(c){
 return field('name','Name des SIP-Zugangs',c.name||'',{required:true,max:80,placeholder:'Zum Beispiel Festnetz-Anschluss'})+
 field('provider','Anbieter',c.provider||'custom',{options:Object.entries(providers).map(([value,p])=>({value,label:p.name}))})+
 '<p id="providerHint" class="inline-info">'+e(providers[c.provider||'custom']?.hint||'')+'</p>'+
 field('auth_mode','Anmeldung',c.auth_mode||'password',{options:[{value:'password',label:'SIP-Benutzername und Passwort'},{value:'access',label:'Anschlussbasiert (Telekom Privatkunden)'}]})+
 '<div id="authFields"><div class="form-grid">'+field('auth_username','SIP-Benutzername / Auth-ID',c.auth_username||'',{max:120})+field('auth_password','SIP-Passwort','',{type:'password',max:256,placeholder:c.auth_password_set?'Gespeichert · leer lassen zum Behalten':'Passwort des SIP-Zugangs'})+'</div><p class="inline-info">Bei geänderten Anmeldedaten das Passwort erneut eintragen. Es wird nach dem Speichern nicht mehr angezeigt.</p></div>'+
 '<div class="form-grid">'+field('registrar','Registrar',c.registrar||'',{placeholder:'sip.anbieter.de'})+field('domain','SIP-Domain',c.domain||'',{placeholder:'anbieter.de'})+'</div>'+
 '<details class="details"><summary>Erweiterte SIP-Einstellungen</summary><div class="form-grid">'+['client_user','contact_user','from_user','realm','outbound_proxy','stun_server'].map((key,i)=>field(key,['Anmelde-ID (Client-User)','Eingehende Ziel-ID','Absender-ID','Realm','Outbound-Proxy','STUN-Server'][i],c[key]||'')).join('')+'</div>'+field('transport','Transport',c.transport||'udp',{options:[{value:'udp',label:'UDP'},{value:'tcp',label:'TCP'}]})+'</details>'+
 switchField('enabled','Beim Anwenden registrieren',c.enabled===true,'Entwurf speichern stellt noch keine Verbindung zum Anbieter her.');
}
function numberEditor(n){
 const used=draft.numbers.filter(x=>x.id!==n.id).map(x=>x.connection_id);
 return field('name','Name der Rufnummer',n.name||'',{required:true,max:80,placeholder:'Zum Beispiel Zentrale'})+
 field('number','Telefonnummer',n.number||'',{type:'tel',required:true,max:16,placeholder:'+Landesvorwahl und Rufnummer'})+
 field('connection_id','SIP-Zugang',n.connection_id||draft.connections.find(c=>!used.includes(c.id))?.id||'',{required:true,options:[{value:'',label:'SIP-Zugang auswählen'},...draft.connections.map(c=>({value:c.id,label:c.name+(used.includes(c.id)?' · bereits zugeordnet':''),disabled:used.includes(c.id)}))],help:'Dieser Gateway-Kern unterstützt eine Rufnummer pro SIP-Login.'})+
 field('incoming_mode','Eingehende Anrufe',n.incoming_mode||'normal',{options:[{value:'normal',label:'An Kiosks klingeln'},{value:'reject',label:'Abweisen'},{value:'announcement',label:'Durchsage von erlaubten Absendern'}]})+
 '<div id="ringFields"><div class="editor-section"><h3>Klingelziele</h3>'+field('ring_mode','Klingeln an',(n.incoming_devices||[]).length?'selected':'all',{options:[{value:'all',label:'Allen aktiven Kiosks'},{value:'selected',label:'Ausgewählten Kiosks'}]})+'<div class="targets-grid" id="targetOptions">'+draft.devices.filter(d=>d.enabled).map(d=>'<label class="check-option"><input type="checkbox" name="targets" value="'+e(d.extension)+'"'+((n.incoming_devices||[]).includes(d.extension)?' checked':'')+'>'+e(d.name)+'<small>'+e(d.extension)+'</small></label>').join('')+(draft.audio.phone_password_set&&!draft.devices.some(d=>d.extension==='100')?'<label class="check-option"><input type="checkbox" name="targets" value="100"'+((n.incoming_devices||[]).includes('100')?' checked':'')+'>Telefon 100<small>100</small></label>':'')+'</div><p class="inline-info">Sobald ein Kiosk annimmt, hören die anderen auf zu klingeln.</p></div></div>'+
 '<div id="announcementFields" class="editor-section"><h3>Durchsage</h3>'+field('announcement_callers','Erlaubte Absender',(n.announcement_callers||[]).join('\n'),{type:'textarea',help:'Eine internationale Rufnummer pro Zeile. Unterdrückte und andere Absender werden abgewiesen.'})+field('announcement_pin','Optionale PIN','',{type:'password',max:6,minLength:6,placeholder:n.announcement_pin_set?'PIN gespeichert · leer lassen zum Behalten':'Sechs Ziffern'})+switchField('announcement_clear_pin','Gespeicherte PIN entfernen',false)+field('announcement_max_seconds','Maximale Dauer (Sekunden)',n.announcement_max_seconds||180,{type:'number',min:10,maxNumber:600})+switchField('announcement_auto_answer','Auto-Answer anfordern',n.announcement_auto_answer===true,'Nur für Durchsagen; das SIP-Ziel muss dies unterstützen.')+'</div>';
}
function deviceEditor(d){
 const used=draft.devices.map(x=>Number(x.extension));let ext=101;while(used.includes(ext)&&ext<199)ext++;
 return '<div class="form-grid">'+field('name','Kioskname',d.name||'',{required:true,max:80,placeholder:'Zum Beispiel Flur'})+field('room','Raum',d.room||'',{max:80,placeholder:'Optional'})+'</div>'+
 field('address','Kiosk IPv4-Adresse',d.address||'',{placeholder:'Optional · Geräteadresse',help:'Wird nur als Geräteinformation gespeichert. Die Anmeldung erfolgt über SIP.'})+
 '<div class="editor-section"><h3>Geräte-Anmeldung</h3><div class="form-grid">'+field('extension','Eigene Nebenstelle',d.extension||String(ext),{required:true,max:3,readonly:d.extension==='100',help:d.extension==='100'?'Übernommene Nebenstelle · bestehende Anmeldung bleibt erhalten':'101 bis 199 · eine Nebenstelle pro Gerät'})+field('password','Geräte-SIP-Passwort','',{type:'password',minLength:12,max:256,placeholder:d.password_set?'Gespeichert · leer lassen zum Behalten':'Mindestens zwölf Zeichen'})+'</div><p class="inline-info">Diese Nebenstelle und dieses Gerätepasswort gehören in das native SIP-Plugin des Kiosks. Die Anbieter-Zugangsdaten bleiben am SIP-Zugang.</p></div>'+
 switchField('enabled','Kiosk aktivieren',d.enabled!==false,'Kann nach dem Anwenden Anrufe annehmen.');
}
function contactEditor(c){return field('name','Kontaktname',c.name||'',{required:true,max:80})+field('number','Telefonnummer',c.number||'',{required:true,type:'tel',max:20})+field('room','Raum / Notiz',c.room||'',{max:80})+switchField('favorite','Als Favorit anzeigen',c.favorite===true);}
function audioEditor(){
 const a=draft.audio;
 return '<p class="inline-info">Native Kiosks verwenden ihre eigenen Nebenstellen. Hier liegen die alternative Einzelanmeldung und die optionale Intercom-Brücke.</p>'+
 field('audio_target','Audio-Ziel',a.audio_target,{options:[{value:'sip',label:'Native SIP-Geräte'},{value:'kiosk',label:'Alternative KS-Intercom-Brücke'}]})+
 (draft.devices.some(d=>d.extension==='100')?'<p class="inline-info">Die übernommene Nebenstelle 100 wird unter Kiosks & Geräte verwaltet.</p>':field('phone_password','Passwort für Einzelanmeldung 100','',{type:'password',minLength:12,max:256,placeholder:a.phone_password_set?'Gespeichert · leer lassen zum Behalten':'Optional bei zusätzlichen Kiosks'}))+
 '<div id="bridgeFields" class="editor-section"><h3>Intercom-Brücke</h3><div class="form-grid">'+field('kiosk_address','Kiosk-Adresse',a.kiosk_address)+field('kiosk_port','Remote-Admin-/Identitätsport',a.kiosk_port,{type:'number'})+'</div>'+field('intercom_key','Gemeinsamer Intercom-Schlüssel','',{type:'password',minLength:16,max:256,placeholder:a.intercom_key_set?'Gespeichert · leer lassen zum Behalten':'Schlüssel aus KS'})+field('intercom_port','Intercom-Rückrufport',a.intercom_port,{type:'number',help:'Standard 8090. Muss von SIP und Web-Port getrennt sein.'})+'</div>';
}
function connectEditor(d){
 return '<div class="notice">'+icon('info')+'<div>Diese Werte im Plugin <strong>SIP Phone for Kiosk Satellite</strong> auf dem Kiosk eintragen.</div></div>'+
 row('PBX address',draft.network.listen_address||'Zuerst Netzwerk einrichten')+row('PBX SIP port',draft.network.sip_port)+row('Device extension',d.extension)+row('Device SIP password',d.password_set?'Das für diesen Kiosk vergebene Passwort':'Noch kein Gerätepasswort gespeichert')+
 '<p class="inline-info">Nach „Änderungen anwenden“ und erfolgreicher Anmeldung zeigt das Plugin „Bereit“. Für den lokalen Echo-Test 600 wählen.</p>';
}
function formValue(form,key){const el=form.elements.namedItem(key);return el?.type==='checkbox'?el.checked:el?.type==='password'?el.value:(el?.value||'').trim();}
function updateAuthVisibility(){const form=$('editorForm');$('authFields').hidden=formValue(form,'auth_mode')==='access';}
function updateNumberVisibility(){const form=$('editorForm');$('ringFields').hidden=formValue(form,'incoming_mode')!=='normal';$('announcementFields').hidden=formValue(form,'incoming_mode')!=='announcement';$('targetOptions').hidden=formValue(form,'ring_mode')==='all';}
function updateAudioVisibility(){$('bridgeFields').hidden=formValue($('editorForm'),'audio_target')!=='kiosk';}
async function saveEditor(event){
 event.preventDefault();if(!editor)return;if(editor.kind==='connect'){closeEditor();return;}
 const next=structuredClone(draft),form=$('editorForm'),kind=editor.kind;
 let value={...(editor.original||{}),id:editor.id||uid(kind[0])};
 if(kind==='accounts'){
  for(const key of ['name','provider','auth_mode','auth_username','auth_password','registrar','domain','client_user','contact_user','from_user','realm','outbound_proxy','transport','stun_server','enabled'])value[key]=formValue(form,key);
 }else if(kind==='numbers'){
  for(const key of ['name','number','connection_id','incoming_mode','announcement_pin','announcement_clear_pin','announcement_auto_answer'])value[key]=formValue(form,key);
  value.number=value.number.replace(/\s/g,'');value.announcement_callers=formValue(form,'announcement_callers').split(/[\n,]/).map(x=>x.trim()).filter(Boolean);
  value.announcement_max_seconds=Number(formValue(form,'announcement_max_seconds'));
  value.incoming_devices=formValue(form,'ring_mode')==='all'?[]:[...form.querySelectorAll('input[name="targets"]:checked')].map(el=>el.value);
  if(formValue(form,'incoming_mode')==='normal'&&formValue(form,'ring_mode')==='selected'&&!value.incoming_devices.length){toast('Mindestens einen Kiosk auswählen oder „Alle aktiven Kiosks“ verwenden.',true);return;}
  if(!next.outbound_number&&value.incoming_mode==='normal')next.outbound_number=value.id;
 }else if(kind==='devices'){
  for(const key of ['name','room','address','extension','password','enabled'])value[key]=formValue(form,key);
 }else if(kind==='contacts'){
  for(const key of ['name','number','room','favorite'])value[key]=formValue(form,key);
  value.number=value.number.replace(/\s/g,'');
 }else if(kind==='audio'){
  for(const key of ['phone_password','audio_target','kiosk_address','intercom_key'])next.audio[key]=formValue(form,key);
  for(const key of ['kiosk_port','intercom_port'])next.audio[key]=Number(formValue(form,key));
 }
 if(kind!=='audio'){const listKey=kind==='accounts'?'connections':kind;const index=next[listKey].findIndex(i=>i.id===value.id);if(index<0)next[listKey].push(value);else next[listKey][index]=value;}
 if(await save(next))closeEditor();
}
async function remove(kind,id){
 const listKey=kind==='accounts'?'connections':kind;const item=draft[listKey].find(x=>x.id===id);
 if(kind==='accounts'&&draft.numbers.some(n=>n.connection_id===id)){toast('Diesen SIP-Zugang zuerst aus seiner Rufnummer lösen oder die Rufnummer entfernen.',true);return;}
 if(kind==='devices'&&draft.numbers.some(n=>n.incoming_devices.includes(item.extension))){toast('Diesen Kiosk zuerst aus den Klingelzielen der Rufnummern entfernen.',true);return;}
 if(!confirm('„'+item.name+'“ aus dem Entwurf entfernen? Die laufende Konfiguration ändert sich erst nach dem Anwenden.'))return;
 const next=structuredClone(draft);next[listKey]=next[listKey].filter(x=>x.id!==id);
 if(kind==='numbers'&&next.outbound_number===id)next.outbound_number='';
 await save(next);
}
async function reset(sample){
 if((draft.connections.length||draft.devices.length||draft.numbers.length)&&!confirm('Den gespeicherten Entwurf durch '+(sample?'Beispieldaten':'eine leere Konfiguration')+' ersetzen? Die laufende Konfiguration bleibt bis zum Anwenden erhalten.'))return;
 try{adopt(await api('api/setup/workspace/reset',{revision:state.revision,sample}));toast(sample?'Beispieldaten geladen. Es werden keine echten Verbindungen aufgebaut.':'Leere Konfiguration bereit.');}catch(error){toast(error.message,true);}
}
async function refreshStatus(showToast=false){
 try{const response=await api('api/status');live=response;if(!editor&&!formDirty)render();if(showToast)toast('Status aktualisiert.');}catch(error){if(showToast)toast(error.message,true);}
}
async function handleAction(button){
 const actionName=button.dataset.action,id=button.dataset.id;
 if(actionName?.startsWith('add-')){
  const kind=actionName.slice(4);
  if(kind==='numbers'&&!draft.connections.length){toast('Zuerst einen SIP-Zugang anlegen.',true);openEditor('accounts');return;}
  openEditor(kind);return;
 }
 if(actionName?.startsWith('edit-')){const kind=actionName.slice(5);openEditor(kind,draft[kind==='accounts'?'connections':kind].find(x=>x.id===id));return;}
 if(actionName?.startsWith('delete-')){await remove(actionName.slice(7),id);return;}
 if(actionName==='connect-device')openEditor('connect',draft.devices.find(d=>d.id===id));
 if(actionName==='audio-settings')openEditor('audio');
 if(actionName==='reset-sample')await reset(true);
 if(actionName==='reset-blank')await reset(false);
 if(actionName==='refresh')await refreshStatus(true);
 if(actionName==='export'){
  const blob=new Blob([JSON.stringify(draft,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='sip-phone-workspace-without-secrets.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 if(actionName==='probe'||actionName==='echo'){
  if(!live.media_bridge){toast('Zuerst die Intercom-Brücke einrichten und anwenden.',true);return;}
  if(actionName==='echo'&&!confirm('Lokalen Echo-Test auf dem konfigurierten Kiosk starten?'))return;
  try{const data=await api(actionName==='probe'?'api/intercom/probe':'api/intercom/test',{});toast(data.message);await refreshStatus();}catch(error){toast(error.message,true);}
 }
}
document.addEventListener('click',event=>{const button=event.target.closest('[data-action]');if(button&&!busy)handleAction(button).catch(error=>toast(error.message,true));});
$('editorForm').addEventListener('submit',saveEditor);
$('closeEditor').addEventListener('click',closeEditor);$('cancelEditor').addEventListener('click',closeEditor);
$('editorBackdrop').addEventListener('click',event=>{if(event.target===$('editorBackdrop'))closeEditor();});
document.addEventListener('keydown',event=>{
 if(event.key==='Escape'&&editor)closeEditor();
 if(event.key==='Tab'&&editor){const items=[...$('editorBackdrop').querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea')].filter(el=>el.getClientRects().length);const first=items[0],last=items[items.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}
});
$('editorForm').addEventListener('change',event=>{
 if(!editor)return;const form=$('editorForm');
 if(editor.kind==='accounts'&&event.target.name==='provider'){
  const p=providers[event.target.value]||{};
  for(const key of ['registrar','domain','realm','stun_server','outbound_proxy','client_user','contact_user','from_user'])form.elements.namedItem(key).value=p[key]||'';
  form.elements.namedItem('auth_mode').value=p.auth_mode||'password';form.elements.namedItem('auth_username').value=p.auth_mode==='access'?'anonymous@t-online.de':'';
  form.elements.namedItem('auth_password').value='';form.elements.namedItem('auth_password').placeholder='Passwort des neuen SIP-Zugangs';$('providerHint').textContent=p.hint||'';updateAuthVisibility();
 }
 if(editor.kind==='accounts'&&event.target.name==='auth_mode')updateAuthVisibility();
 if(editor.kind==='numbers')updateNumberVisibility();
 if(editor.kind==='audio')updateAudioVisibility();
});
document.addEventListener('submit',async event=>{
 if(event.target.id!=='networkForm')return;event.preventDefault();
 const form=event.target,next=structuredClone(draft);
 for(const key of ['listen_address','local_network','external_address'])next.network[key]=formValue(form,key);
 next.network.sip_port=Number(formValue(form,'sip_port'));next.runtime_enabled=formValue(form,'runtime_enabled');
 for(const key of ['lan_enabled','web_username','web_password'])next.web[key]=formValue(form,key);
 await save(next);
});
document.addEventListener('input',event=>{if(event.target.closest('#networkForm'))formDirty=true;});
document.addEventListener('change',async event=>{
 if(event.target.id==='outboundSelect'){const next=structuredClone(draft);next.outbound_number=event.target.value;await save(next);}
 if(event.target.closest('#networkForm'))formDirty=true;
});
function navigate(){
 const desired=location.hash.slice(1);const next=pages[desired]?desired:'overview';
 if(formDirty&&next!==page&&!confirm('Ungespeicherte Netzwerkänderungen verwerfen?')){history.replaceState(null,'','#'+page);return;}
 page=next;formDirty=false;$('sidebar')?.classList.remove('open');document.querySelector('.sidebar').classList.remove('open');render();
}
window.addEventListener('hashchange',navigate);
window.addEventListener('beforeunload',event=>{if(formDirty){event.preventDefault();event.returnValue='';}});
$('menuToggle').addEventListener('click',()=>document.querySelector('.sidebar').classList.toggle('open'));
$('themeToggle').addEventListener('click',()=>{const next=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=next;try{localStorage.setItem('sip-phone-workspace-theme',next);}catch{}});
try{document.documentElement.dataset.theme=localStorage.getItem('sip-phone-workspace-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');}catch{}
$('applyButton').addEventListener('click',async()=>{
 if(formDirty){toast('Die Netzwerkänderungen zuerst als Entwurf speichern.',true);return;}
 if(draft.demo){toast('Beispieldaten können nicht aktiviert werden. Starte eine eigene Konfiguration.',true);return;}
 if(draft.runtime_enabled&&!confirm('Konfiguration anwenden und den Telefonserver neu starten?'))return;
 busy=true;setBusy();try{const result=await api('api/setup/workspace/apply',{revision:state.revision});adopt(result);toast(result.message);}catch(error){toast(error.message,true);}finally{busy=false;setBusy();}
});
async function load(){try{const result=await api('api/setup/workspace');providers=result.providers;state=result;draft=result.draft;live=result.status;navigate();setBusy();}catch(error){$('pageContent').innerHTML='<div class="card empty-state"><h2>Verbindung nicht verfügbar</h2><p>'+e(error.message)+'</p><button class="button" data-action="reload">Erneut versuchen</button></div>';toast(error.message,true);}}
document.addEventListener('click',event=>{if(event.target.closest('[data-action="reload"]'))load();});
setInterval(()=>{if(state)refreshStatus();},15000);
load();
