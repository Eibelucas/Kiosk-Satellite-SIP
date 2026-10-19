// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip.nativephone;

import android.os.Handler;
import android.os.Looper;
import java.util.*;
import me.jxl.kiosk.plugins.*;

/** Separate experimental plugin ID: native floating dialer and direct SIP to Asterisk 100. */
public final class NativePhonePlugin implements KioskPlugin,FloatingDialer.Actions {
    private final Handler main=new Handler(Looper.getMainLooper());
    private final DialerModel model=new DialerModel();
    private volatile PluginHost host;
    private volatile NativeSipClient client;
    private volatile FloatingDialer view;
    private int generation;
    private boolean intercomBusy,voiceBusy,wakeListening;
    private final Runnable tick=new Runnable(){public void run(){if(host==null)return;if(view!=null)view.refresh();if(model.active()){try{host.executeCommand("postponeScreensaver",Collections.emptyMap(),(ok,data,error)->{});}catch(Exception ignored){}}main.postDelayed(this,1000);}};
    public void start(PluginHost host,Map<String,Object> settings){this.host=host;configure(settings);for(String event:new String[]{"intercom.state","voice.state","wakeword.state"})try{host.subscribe(event);}catch(Exception ignored){}read("getIntercomState","intercom");read("getVoiceState","voice");read("getWakeWordState","wake");main.post(tick);}
    private void read(String command,String kind){PluginHost h=host;try{h.executeCommand(command,Collections.emptyMap(),(ok,data,error)->{if(h==host&&ok&&data instanceof Map)main.post(()->{if(h==host)observe(kind,(Map<?,?>)data);});});}catch(Exception ignored){}}
    public void configure(Map<String,Object> settings){
        final int rev=++generation;NativeSipClient old=client;client=null;if(old!=null)old.stop();
        final String server=text(settings,"server",""),password=text(settings,"password",""),extension=text(settings,"extension","100");
        final int port=integer(settings,"port",5070),localPort=integer(settings,"localPort",5090),bottom=Math.max(12,Math.min(300,integer(settings,"bottomOffset",88)));
        final String side="left".equals(text(settings,"side","right"))?OverlaySpec.BOTTOM_LEFT:OverlaySpec.BOTTOM_RIGHT;
        main.post(()->{if(rev!=generation||host==null)return;model.registered=false;model.update("idle","","SIP einrichten: HA-IP, eigene Nebenstelle und SIP-Passwort.");if(view==null)view=new FloatingDialer(model,this);try{host.showOverlay("native_phone",OverlaySpec.at(side).inset(12,12,12,bottom).onTop(true).closeOnBack(false),view);}catch(Exception e){host.status("Native Overlays fehlen. Kiosk Satellite aktualisieren.",true);}});
        try{
            NativeSipClient fresh=new NativeSipClient(new NativeSipClient.Config(server,port,extension,password,localPort),new NativeSipClient.Events(){
                public void registration(boolean ready){main.post(()->{if(rev!=generation||host==null)return;model.registered=ready;if(!model.active())model.detail=ready?"Bereit · Nebenstelle "+extension:"SIP nicht angemeldet";refresh();});}
                public void call(String state,String peer,String detail){main.post(()->{if(rev!=generation||host==null)return;model.update(state,peer,detail);if(state.equals("incoming")){try{host.executeCommand("screenOn",Collections.emptyMap(),(ok,data,error)->{});}catch(Exception ignored){}}refresh();});}
            },address->new AndroidG711(address,view==null?null:view.audioContext()));
            client=fresh;fresh.start();
        }catch(IllegalArgumentException problem){main.post(()->{if(rev==generation&&host!=null){model.detail=problem.getMessage();refresh();}});}
    }
    private void observe(String kind,Map<?,?> payload){String state=String.valueOf(payload.get("state"));if(kind.equals("intercom"))intercomBusy=!Arrays.asList("idle","missed","null").contains(state);if(kind.equals("voice"))voiceBusy=Boolean.TRUE.equals(payload.get("enabled"))&&!Arrays.asList("idle","null").contains(state);if(kind.equals("wake"))wakeListening=Boolean.TRUE.equals(payload.get("listening"));if(model.active()&&(intercomBusy||voiceBusy||wakeListening)){NativeSipClient c=client;if(c!=null)c.hangup();}}
    public void onEvent(String event,Map<String,Object> payload){if(payload==null)return;Map<String,Object> copy=new HashMap<>(payload);main.post(()->{if(host==null)return;if(event.equals("ks.intercom.state"))observe("intercom",copy);if(event.equals("ks.voice.state"))observe("voice",copy);if(event.equals("ks.wakeword.state"))observe("wake",copy);});}
    public void execute(String command,Map<String,Object> args){main.post(()->{if(host==null)return;if(command.equals("toggleDialer"))toggle();else if(command.equals("openPhone")){model.expanded=true;refresh();}else if(command.equals("hangup"))hangup();});}
    public void toggle(){if(host==null)return;model.expanded=!model.expanded;refresh();}
    private boolean audioAllowed(){if(intercomBusy||voiceBusy||wakeListening){model.detail="Audio belegt. Für diesen Test Wake Word und Sprachaufnahme pausieren.";refresh();return false;}return true;}
    public void dial(String number){if(!audioAllowed())return;NativeSipClient c=client;if(c==null)return;try{model.number=number;model.update("calling",number,"Verbindet …");refresh();c.dial(number);}catch(RuntimeException e){model.update("error","",e.getMessage());refresh();}}
    public void answer(){if(audioAllowed()){NativeSipClient c=client;if(c!=null)c.answer();}}
    public void hangup(){NativeSipClient c=client;if(c!=null)c.hangup();}
    public void mute(){model.muted=!model.muted;NativeSipClient c=client;if(c!=null)c.mute(model.muted);refresh();}
    private void refresh(){if(view!=null)view.refresh();PluginHost h=host;if(h!=null)try{h.status(model.label(),!model.registered&&!model.active());}catch(Exception ignored){}}
    public void stop(){host=null;generation++;main.removeCallbacksAndMessages(null);NativeSipClient old=client;client=null;if(old!=null)old.stop();}
    private static String text(Map<String,Object> s,String k,String fallback){Object value=s==null?null:s.get(k);return value instanceof String?(String)value:fallback;}
    private static int integer(Map<String,Object> s,String k,int fallback){try{return Integer.parseInt(text(s,k,String.valueOf(fallback)));}catch(Exception e){return fallback;}}
}
