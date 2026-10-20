// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip.nativephone;

/** View-independent state; hiding the dialer never hangs up a call. */
public final class DialerModel {
    public String number="", peer="", state="idle", detail="Connecting to SIP …";
    public String mutedLabel="Microphone muted";
    public boolean expanded, registered, muted;
    public long connectedAt;
    public boolean active(){return !state.equals("idle")&&!state.equals("error");}
    public boolean canDial(){return registered&&!active()&&number.matches("\\+?[0-9*#]{3,20}");}
    public void digit(String value){if(!active()&&value.matches("[0-9*#]")&&number.length()<20)number+=value;}
    public void plus(){if(!active()&&number.isEmpty())number="+";}
    public void delete(){if(!active()&&!number.isEmpty())number=number.substring(0,number.length()-1);}
    public void update(String next,String who,String message){
        if(next.equals("busy"))return;
        if(!who.isEmpty())peer=who;
        if(next.equals("calling")){peer=number;muted=false;expanded=true;}
        if(next.equals("incoming")){muted=false;expanded=true;}
        if(next.equals("connected")&&!state.equals("connected"))connectedAt=System.nanoTime();
        state=next;detail=message;
        if(next.equals("idle")||next.equals("error")){muted=false;connectedAt=0;}
    }
    public String label(){
        if(!state.equals("connected"))return detail;
        long seconds=Math.max(0,(System.nanoTime()-connectedAt)/1_000_000_000);
        return String.format(java.util.Locale.ROOT,"%02d:%02d%s",seconds/60,seconds%60,muted?" · "+mutedLabel:"");
    }
}
