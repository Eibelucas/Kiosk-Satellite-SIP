// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip.nativephone;

import java.util.*;
import java.util.function.Consumer;

/** Serialized, asynchronous wake-word mute ownership for one user-started call.
 * All callbacks and delayed tasks must run on the same executor as acquire/release.
 */
final class WakeWordGuard {
    interface Result { void done(boolean ok,Object data); }
    interface Bridge {
        void command(String name,Map<String,Object> args,Result result);
        void later(Runnable task,long delayMs);
    }
    private enum Phase { IDLE, READING, MUTING, VERIFYING, HELD, RESTORING }
    private final Bridge bridge;
    private final Consumer<String> warning;
    private Phase phase=Phase.IDLE;
    private long ticket;
    private boolean wanted,muteRequested;
    private Runnable ready;
    private Consumer<String> rejected;
    WakeWordGuard(Bridge bridge,Consumer<String> warning){this.bridge=bridge;this.warning=warning;}
    boolean busy(){return phase!=Phase.IDLE;}
    void acquire(Runnable ready,Consumer<String> rejected){
        if(busy()){rejected.accept("Wake word is being restored. Try again shortly.");return;}
        this.ready=ready;this.rejected=rejected;wanted=true;muteRequested=false;phase=Phase.READING;
        final long run=++ticket;
        command("getWakeWordState",Collections.emptyMap(),(ok,data)->{
            if(run!=ticket||phase!=Phase.READING)return;
            if(!wanted){restore();return;}
            if(!ok||!(data instanceof Map)){fail("Cannot read wake word state. Pause wake word in Kiosk Satellite before calling.");return;}
            Map<?,?> state=(Map<?,?>)data;
            boolean listening=Boolean.TRUE.equals(state.get("listening"));
            boolean enabled=Boolean.TRUE.equals(state.get("enabled"))||Boolean.TRUE.equals(state.get("active"))||listening;
            if(!enabled&&!listening){allow();return;}
            if(!(state.get("muted") instanceof Boolean)){fail("Cannot read wake word mute state. Pause wake word in Kiosk Satellite before calling.");return;}
            if(Boolean.TRUE.equals(state.get("muted"))){
                if(listening)fail("Wake word still owns the microphone. Pause wake word in Kiosk Satellite before calling.");
                else allow();
                return;
            }
            phase=Phase.MUTING;muteRequested=true;
            command("setWakeWordMuted",Collections.singletonMap("muted",true),(muted,ignored)->{
                if(run!=ticket||phase!=Phase.MUTING)return;
                // A timed-out control may still have applied, so release even on failure.
                if(!wanted){restore();return;}
                if(!muted){fail("Cannot mute wake word. Pause wake word in Kiosk Satellite before calling.");return;}
                phase=Phase.VERIFYING;verify(run,10);
            });
        });
    }
    private void verify(long run,int remaining){
        if(run!=ticket||phase!=Phase.VERIFYING)return;
        if(!wanted){restore();return;}
        command("getWakeWordState",Collections.emptyMap(),(ok,data)->{
            if(run!=ticket||phase!=Phase.VERIFYING)return;
            if(!wanted){restore();return;}
            if(ok&&data instanceof Map){
                Map<?,?> state=(Map<?,?>)data;
                if(Boolean.FALSE.equals(state.get("listening"))&&Boolean.TRUE.equals(state.get("muted"))){allow();return;}
            }
            if(remaining<=1){fail("Wake word still owns the microphone. Pause wake word in Kiosk Satellite before calling.");return;}
            bridge.later(()->verify(run,remaining-1),250);
        });
    }
    private void allow(){
        if(!wanted){restore();return;}
        phase=Phase.HELD;Runnable action=ready;ready=null;rejected=null;action.run();
    }
    private void fail(String message){
        Consumer<String> callback=rejected;boolean notify=wanted;
        wanted=false;ready=null;rejected=null;
        restore();
        if(notify&&callback!=null)callback.accept(message);
    }
    void release(){
        wanted=false;ready=null;rejected=null;
        // Do not race a pending mute: wait for its completion before restoring.
        if(phase==Phase.HELD||phase==Phase.VERIFYING)restore();
    }
    private void restore(){
        if(phase==Phase.RESTORING)return;
        if(!muteRequested){phase=Phase.IDLE;return;}
        phase=Phase.RESTORING;final long run=ticket;
        command("setWakeWordMuted",Collections.singletonMap("muted",false),(ok,data)->{
            if(run!=ticket||phase!=Phase.RESTORING)return;
            muteRequested=false;phase=Phase.IDLE;
            if(!ok)warning.accept("Could not restore wake word. Check its mute switch in Kiosk Satellite.");
        });
    }
    /** The host revokes commands before stop; do not issue API calls from stop. */
    void abandon(){ticket++;wanted=false;ready=null;rejected=null;muteRequested=false;phase=Phase.IDLE;}
    private void command(String name,Map<String,Object> args,Result result){
        try{bridge.command(name,args,result);}catch(RuntimeException failure){result.done(false,null);}
    }
}
