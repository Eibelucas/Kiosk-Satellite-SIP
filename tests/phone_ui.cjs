// Exercise the real phone script without a browser, provider or outgoing call.
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../kiosk_sip/app/static/phone.js'), 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));

function start({hash='', bridge=true, registered=true, confirm=true}={}) {
  const nodes = new Map(), requests=[], events={};
  let finishContacts;
  const contactReply = new Promise(resolve => { finishContacts = resolve; });
  function element() {
    const e={value:'',textContent:'',className:'',disabled:false,hidden:false,
      children:[],handlers:{},attributes:{},selectedIndex:-1,
      addEventListener(name,handler){this.handlers[name]=handler;},
      setAttribute(name,value){this.attributes[name]=value;},
      appendChild(child){this.children.push(child);},
      replaceChildren(){this.children=[];}};
    Object.defineProperty(e,'options',{get(){return this.children;}});
    return e;
  }
  function get(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);}
  const window={location:{hash},confirm(){return confirm;},
    addEventListener(name,handler){events[name]=handler;}};
  const context=vm.createContext({document:{getElementById:get,
    querySelector:()=>({content:'fake-csrf'}),querySelectorAll:()=>[],createElement:element},
    window,setInterval(){},fetch:async(url,options)=>{
      requests.push({url,options});
      return {ok:true,json:async()=>url==='api/contacts'?contactReply:
        url==='api/status'?{audio_target:'kiosk',phone_registered:false,media_bridge:bridge,
          outbound_line:'main',intercom:{state:'bereit'},lines:[{id:'main',enabled:true,
            incoming_mode:'normal',registered,label:'Test',state:'registriert',phone_number:'+4900001234567'}]}:
          {message:'accepted'}};
    }});
  vm.runInContext(source,context);
  return {get,requests,window,events,finishContacts};
}

(async()=>{
  const initial=start();
  assert.equal(initial.get('dialerPanel').hidden,false);
  assert.equal(initial.get('contactsPanel').hidden,true);
  assert.equal(initial.get('searchLabel').hidden,true);
  initial.finishContacts([]);await tick();
  assert.equal(initial.get('dialerPanel').hidden,false);
  assert.equal(initial.get('showDialer').attributes['aria-pressed'],'true');

  const changed=start();
  changed.get('showContacts').handlers.click();
  changed.finishContacts([]);await tick();
  assert.equal(changed.get('contactsPanel').hidden,false,'late contacts must preserve selected view');
  assert.equal(changed.get('dialerPanel').hidden,true);

  const shortcut=start({hash:'#contacts'});
  shortcut.finishContacts([{name:'Testkontakt',number:'+4900001234567',kind:'phone',favorite:true}]);
  await tick();
  assert.equal(shortcut.get('contactsPanel').hidden,false);
  shortcut.get('contactsPanel').children[0].handlers.click();
  assert.equal(shortcut.get('number').value,'+4900001234567');
  assert.equal(shortcut.get('dialerPanel').hidden,false);
  assert.equal(shortcut.requests.filter(x=>x.url==='api/call').length,0,'contact selection never places a call');
  shortcut.window.location.hash='#contacts';shortcut.events.hashchange();
  assert.equal(shortcut.get('contactsPanel').hidden,false,'same-page contact shortcut');

  for (const opts of [{bridge:false},{registered:false},{confirm:false},{}]) {
    const ui=start(opts);ui.finishContacts([]);await tick();
    assert.equal(ui.get('call').disabled,opts.bridge===false||opts.registered===false);
    ui.get('number').value='+4900001234567';
    if(!ui.get('call').disabled)await ui.get('call').handlers.click();
    const posts=ui.requests.filter(x=>x.url==='api/call');
    assert.equal(posts.length,Object.keys(opts).length?0:1);
    if(posts.length){assert.equal(posts[0].options.headers['X-CSRF-Token'],'fake-csrf');
      assert.deepEqual(JSON.parse(posts[0].options.body),{number:'+4900001234567',line:'main'});}
  }
  console.log('PASS: default dialer, direct contacts, deferred view preservation, selection without call, audio/registration guards, confirmation and CSRF.');
})().catch(error=>{console.error(error);process.exitCode=1;});
