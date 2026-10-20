// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip.nativephone;

import android.os.Handler;
import android.os.Looper;
import java.util.*;
import me.jxl.kiosk.plugins.*;

/** Native floating SIP phone connected to the configured PBX. */
public final class NativePhonePlugin implements KioskPlugin,FloatingDialer.Actions {
    private final Handler main=new Handler(Looper.getMainLooper());
    private final DialerModel model=new DialerModel();
    private volatile PluginHost host;
    private volatile NativeSipClient client;
    private volatile FloatingDialer view;
    private volatile int generation;
    private PhoneText text=new PhoneText("English");
    private WakeWordGuard wake;
    private boolean intercomBusy,voiceBusy,preparing;
    private long intercomEvent,voiceEvent;
    private final Runnable tick=new Runnable(){public void run(){
        if(host==null)return;
        if(view!=null)view.refresh();
        if(model.active())try{host.executeCommand("postponeScreensaver",Collections.emptyMap(),(ok,data,error)->{});}catch(Exception ignored){}
        main.postDelayed(this,1000);
    }};
    public void start(PluginHost host,Map<String,Object> settings){
        this.host=host;
        main.post(()->{
            wake=new WakeWordGuard(new WakeWordGuard.Bridge(){
                public void command(String name,Map<String,Object> args,WakeWordGuard.Result result){
                    PluginHost h=NativePhonePlugin.this.host;
                    if(h==null){result.done(false,null);return;}
                    h.executeCommand(name,args,(ok,data,error)->main.post(()->{
                        if(h==NativePhonePlugin.this.host)result.done(ok,data);
                    }));
                }
                public void later(Runnable task,long delay){main.postDelayed(task,delay);}
            },message->{
                if(model.active())model.detail=text.get(message);
                else model.update("error","",text.get(message));
                refresh();
            });
        });
        configure(settings);
        for(String event:new String[]{"intercom.state","voice.state"})try{host.subscribe(event);}catch(Exception ignored){}
        main.post(()->{read("getIntercomState","intercom");read("getVoiceState","voice");});
        main.post(tick);
    }
    private void read(String command,String kind){
        PluginHost h=host;if(h==null)return;
        long event=kind.equals("intercom")?intercomEvent:voiceEvent;
        try{h.executeCommand(command,Collections.emptyMap(),(ok,data,error)->{
            if(h==host&&ok&&data instanceof Map)main.post(()->{
                long current=kind.equals("intercom")?intercomEvent:voiceEvent;
                if(h==host&&event==current)observe(kind,(Map<?,?>)data);
            });
        });}catch(Exception ignored){}
    }
    public void configure(Map<String,Object> settings){
        final int rev=++generation;NativeSipClient old=client;client=null;if(old!=null)old.stop();
        final String server=value(settings,"server",""),password=value(settings,"password",""),extension=value(settings,"extension","100");
        final PhoneText language=new PhoneText(value(settings,"language","English"));
        final int port=integer(settings,"port",5070),localPort=integer(settings,"localPort",5090),bottom=Math.max(12,Math.min(300,integer(settings,"bottomOffset",88)));
        final String side="left".equals(value(settings,"side","right"))?OverlaySpec.BOTTOM_LEFT:OverlaySpec.BOTTOM_RIGHT;
        main.post(()->{
            if(rev!=generation||host==null)return;
            if(wake!=null)wake.release();preparing=false;text=language;
            model.registered=false;model.mutedLabel=text.get("Microphone muted");
            model.update("idle","",text.get("Set up SIP: PBX address, extension and device password."));
            view=new FloatingDialer(model,this,text);
            try{host.showOverlay("native_phone",OverlaySpec.at(side).inset(12,12,12,bottom).onTop(true).closeOnBack(false),view);}
            catch(Exception e){host.status(text.get("Native overlays unavailable. Update Kiosk Satellite."),true);}
        });
        try{
            NativeSipClient fresh=new NativeSipClient(new NativeSipClient.Config(server,port,extension,password,localPort),new NativeSipClient.Events(){
                public void registration(boolean ready){main.post(()->{
                    if(rev!=generation||host==null)return;
                    model.registered=ready;
                    if(!model.active())model.detail=ready?text.get("Ready · Extension ")+extension:text.get("SIP not registered");
                    refresh();
                });}
                public void call(String state,String peer,String detail){main.post(()->{
                    if(rev!=generation||host==null)return;
                    if(state.equals("idle")||state.equals("error")||state.equals("incoming")){
                        // An incoming dialog can arrive while an outgoing call is still acquiring audio.
                        preparing=false;if(wake!=null)wake.release();
                    }
                    model.update(state,peer,text.get(detail));
                    if(state.equals("incoming")){
                        try{host.executeCommand("screenOn",Collections.emptyMap(),(ok,data,error)->{});}catch(Exception ignored){}
                        if(intercomBusy||voiceBusy)hangup();
                    }
                    refresh();
                });}
            },(address,pbx)->new AndroidG711(address,pbx,view==null?null:view.audioContext()));
            client=fresh;fresh.start();
        }catch(IllegalArgumentException problem){main.post(()->{
            if(rev==generation&&host!=null){model.detail=text.get(problem.getMessage());refresh();}
        });}
    }
    private void observe(String kind,Map<?,?> payload){
        String state=String.valueOf(payload.get("state"));
        if(kind.equals("intercom"))intercomBusy=!Arrays.asList("idle","ended","missed","null").contains(state);
        if(kind.equals("voice"))voiceBusy=!Boolean.FALSE.equals(payload.get("enabled"))&&!Arrays.asList("idle","null").contains(state);
        if(model.active()&&(intercomBusy||voiceBusy))hangup();
    }
    public void onEvent(String event,Map<String,Object> payload){
        if(payload==null)return;Map<String,Object> copy=new HashMap<>(payload);
        main.post(()->{
            if(host==null)return;
            if(event.equals("ks.intercom.state")){intercomEvent++;observe("intercom",copy);}
            if(event.equals("ks.voice.state")){voiceEvent++;observe("voice",copy);}
        });
    }
    public void execute(String command,Map<String,Object> args){main.post(()->{
        if(host==null)return;
        if(command.equals("toggleDialer"))toggle();
        else if(command.equals("openPhone")){model.expanded=true;refresh();}
        else if(command.equals("hangup"))hangup();
    });}
    public void toggle(){if(host==null)return;model.expanded=!model.expanded;refresh();}
    private boolean audioAllowed(){
        if(intercomBusy||voiceBusy){model.detail=text.get("Audio is busy with Voice Satellite or intercom.");refresh();return false;}
        return true;
    }
    public void dial(String number){
        if(preparing||model.active()||!model.registered||!audioAllowed())return;
        model.number=number;
        if(!model.canDial())return;
        prepare(false,number);
    }
    public void answer(){
        if(preparing||!model.state.equals("incoming")||!audioAllowed())return;
        prepare(true,model.peer);
    }
    private void prepare(boolean incoming,String peer){
        NativeSipClient c=client;if(c==null||wake==null||host==null)return;
        final int rev=generation;
        if(wake.busy()){model.detail=text.get("Wake word is being restored. Try again shortly.");refresh();return;}
        preparing=true;model.update("preparing",peer,text.get("Preparing call audio …"));refresh();
        wake.acquire(()->{
            if(!preparing||rev!=generation||host==null||client!=c){wake.release();return;}
            preparing=false;
            if(!audioAllowed()){wake.release();model.update(incoming?"incoming":"error",peer,text.get("Audio is busy with Voice Satellite or intercom."));refresh();return;}
            try{
                if(incoming)c.answer();else c.dial(model.number);
                model.detail=text.get("Connecting …");refresh();
            }catch(RuntimeException failure){wake.release();model.update(incoming?"incoming":"error",peer,text.get(failure.getMessage()));refresh();}
        },message->{
            if(rev!=generation||host==null)return;
            preparing=false;model.update(incoming?"incoming":"error",peer,text.get(message));refresh();
        });
    }
    public void hangup(){
        if(preparing){
            preparing=false;if(wake!=null)wake.release();
            // A pending incoming answer already has a SIP dialog; cancel it too.
            NativeSipClient c=client;if(c!=null)c.hangup();
            model.update("idle","",text.get("Call cancelled."));refresh();return;
        }
        NativeSipClient c=client;if(c!=null)c.hangup();
    }
    public void mute(){model.muted=!model.muted;NativeSipClient c=client;if(c!=null)c.mute(model.muted);refresh();}
    private void refresh(){
        if(view!=null)view.refresh();PluginHost h=host;
        if(h!=null)try{h.status(model.label(),model.state.equals("error")||!model.registered&&!model.active());}catch(Exception ignored){}
    }
    public void stop(){
        host=null;generation++;main.removeCallbacksAndMessages(null);
        main.post(()->{if(wake!=null)wake.abandon();preparing=false;});
        NativeSipClient old=client;client=null;if(old!=null)old.stop();
    }
    private static String value(Map<String,Object> s,String k,String fallback){Object value=s==null?null:s.get(k);return value instanceof String?(String)value:fallback;}
    private static int integer(Map<String,Object> s,String k,int fallback){try{return Integer.parseInt(value(s,k,String.valueOf(fallback)));}catch(Exception e){return fallback;}}
}
