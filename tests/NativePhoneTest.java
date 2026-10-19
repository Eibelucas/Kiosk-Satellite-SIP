// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip.nativephone;

import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.BooleanSupplier;

/** Real UDP transactions against a loopback PBX. No Android microphone or external calls. */
public final class NativePhoneTest {
    static int assertions;
    static void check(boolean ok,String why){assertions++;if(!ok)throw new AssertionError(why);}
    static void await(BooleanSupplier ok,String why)throws Exception{long end=System.currentTimeMillis()+3000;while(!ok.getAsBoolean()&&System.currentTimeMillis()<end)Thread.sleep(10);check(ok.getAsBoolean(),why);}
    static final class Audio implements NativeSipClient.Media {
        int starts,closed;boolean muted;volatile boolean healthy=true;
        public String offer(){return sdp();}public String answer(String sdp){return sdp();}
        public void start(String sdp){starts++;}public void mute(boolean on){muted=on;}public void close(){closed++;}
        public boolean healthy(){return healthy;}
    }
    static String sdp(){return "v=0\r\nc=IN IP4 127.0.0.1\r\nm=audio 30000 RTP/AVP 0\r\na=rtpmap:0 PCMU/8000\r\na=sendrecv\r\n";}
    static final class Fixture implements AutoCloseable {
        DatagramSocket pbx=new DatagramSocket(new InetSocketAddress("127.0.0.1",0));
        NativeSipClient sip;String extension;InetSocketAddress peer;List<Audio> media=new CopyOnWriteArrayList<>();List<String> states=new CopyOnWriteArrayList<>();volatile String state="idle";
        Fixture()throws Exception{this("100");}
        Fixture(String extension)throws Exception{
            this.extension=extension;
            pbx.setSoTimeout(3500);int local;try(DatagramSocket probe=new DatagramSocket(0)){local=probe.getLocalPort();}
            sip=new NativeSipClient(new NativeSipClient.Config("127.0.0.1",pbx.getLocalPort(),extension,"fake-phone-secret",local),new NativeSipClient.Events(){public void registration(boolean ready){}public void call(String s,String p,String d){state=s;states.add(s);}},address->{Audio a=new Audio();media.add(a);return a;});
            sip.start();SipMessage register=receive("REGISTER");send(response(register,401,"Unauthorized","WWW-Authenticate: Digest realm=\"asterisk\", nonce=\"fake-register-nonce\", algorithm=MD5, qop=\"auth\"\r\n",""));
            SipMessage authenticated=receive("REGISTER");check(authenticated.header("authorization")!=null,"REGISTER has digest");check(!authenticated.header("authorization").contains("fake-phone-secret"),"password is not on wire");verifyDigest(authenticated,"REGISTER","fake-register-nonce");
            send(response(authenticated,200,"OK","Expires: 120\r\n",""));await(sip::registered,"registered");
        }
        SipMessage receive(String method)throws Exception{for(int i=0;i<30;i++){DatagramPacket p=new DatagramPacket(new byte[32768],32768);pbx.receive(p);peer=new InetSocketAddress(p.getAddress(),p.getPort());SipMessage m=SipMessage.parse(new String(p.getData(),0,p.getLength(),StandardCharsets.UTF_8));if(m!=null&&method.equals(m.isRequest()?m.method():""+m.status()))return m;}throw new AssertionError("Did not receive "+method);}
        void send(String text)throws Exception{byte[] b=text.getBytes(StandardCharsets.UTF_8);pbx.send(new DatagramPacket(b,b.length,peer));}
        public void close(){sip.stop();pbx.close();}
        String response(SipMessage request,int code,String reason,String extra,String body){return "SIP/2.0 "+code+" "+reason+"\r\nVia: "+request.header("via")+"\r\nFrom: "+request.header("from")+"\r\nTo: "+request.header("to")+(request.header("to").contains(";tag=")?"":";tag=pbx")+"\r\nCall-ID: "+request.header("call-id")+"\r\nCSeq: "+request.header("cseq")+"\r\nContact: <sip:asterisk@127.0.0.1:"+pbx.getLocalPort()+">\r\n"+extra+(body.isEmpty()?"":"Content-Type: application/sdp\r\n")+"Content-Length: "+body.getBytes(StandardCharsets.UTF_8).length+"\r\n\r\n"+body;}
        SipMessage dial()throws Exception{sip.dial("600");SipMessage invite=receive("INVITE");check(invite.startLine.startsWith("INVITE sip:600@"),"direct INVITE to local echo");check(media.get(media.size()-1).starts==0,"microphone not started before remote answer");return invite;}
        void verifyDigest(SipMessage message,String method,String nonce){Map<String,String> p=SipDigest.parseParams(message.header("authorization"));check(p.get("username").equals(extension),"correct per-device digest user");String expected=SipDigest.response(extension,"asterisk","fake-phone-secret",method,p.get("uri"),nonce,p.get("qop"),p.get("nc"),p.get("cnonce"));check(expected.equals(p.get("response")),"correct digest response");}
    }
    public static void main(String[] args)throws Exception{
        model();directCall();cancel();cancelAnswerRace();rejection();incoming();stopActive();spoofedResponse();retransmission();lateAnswerAfterCancel();incomingDeclineRetransmission();mediaFailure();codecs();independentDevices();
        System.out.println("Native phone: "+assertions+" assertions passed (loopback SIP + model)");
    }
    static void model(){DialerModel m=new DialerModel();check(!m.canDial(),"unregistered cannot dial");m.registered=true;m.digit("1");m.digit("0");m.digit("1");check(m.canDial(),"registered number can dial");m.update("calling","101","Verbindet");m.expanded=false;check(m.active(),"collapse preserves call");m.digit("9");check(m.number.equals("101"),"cannot edit active number");m.update("connected","","Verbunden");long time=m.connectedAt;m.update("connected","","Verbunden");check(m.connectedAt==time,"duplicate event preserves duration");m.update("idle","","Beendet");check(m.canDial(),"call can be repeated");m.delete();check(!m.canDial(),"short invalid number rejected");}
    static void directCall()throws Exception{try(Fixture f=new Fixture()){
        SipMessage invite=f.dial();f.send(f.response(invite,401,"Unauthorized","WWW-Authenticate: Digest realm=\"asterisk\", nonce=\"fake-invite-nonce\", algorithm=MD5, qop=\"auth\"\r\n",""));SipMessage ack=f.receive("ACK");check(ack.cseqNumber()==invite.cseqNumber(),"challenge ACK keeps cseq");check(ack.header("via").equals(invite.header("via")),"challenge ACK keeps branch");
        SipMessage authenticated=f.receive("INVITE");check(authenticated.cseqNumber()==invite.cseqNumber()+1,"authenticated INVITE increments cseq");f.verifyDigest(authenticated,"INVITE","fake-invite-nonce");
        f.send(f.response(authenticated,180,"Ringing","",""));await(()->f.state.equals("ringing"),"remote ringing state");
        String ok=f.response(authenticated,200,"OK","",sdp());f.send(ok);f.receive("ACK");await(()->f.state.equals("connected"),"connected without a local answer action");check(f.media.get(0).starts==1,"audio starts once");f.send(ok);f.receive("ACK");check(f.media.get(0).starts==1,"repeated 200 does not reopen mic");
        f.sip.mute(true);await(()->f.media.get(0).muted,"mute forwarded");f.sip.hangup();SipMessage bye=f.receive("BYE");check(bye.header("call-id").equals(invite.header("call-id")),"BYE matches dialog");await(()->f.state.equals("idle"),"local hangup idle");check(f.media.get(0).closed>0,"hangup frees media");
    }}
    static void cancel()throws Exception{try(Fixture f=new Fixture()){
        SipMessage invite=f.dial();f.sip.hangup();await(()->f.state.equals("cancelling"),"cancel pending before provisional");f.send(f.response(invite,180,"Ringing","",""));SipMessage cancel=f.receive("CANCEL");check(cancel.header("via").equals(invite.header("via")),"CANCEL uses invite branch");check(cancel.cseqNumber()==invite.cseqNumber(),"CANCEL uses invite cseq");f.send(f.response(cancel,200,"OK","",""));f.send(f.response(invite,487,"Request Terminated","",""));f.receive("ACK");await(()->f.state.equals("idle"),"cancel ends dialog");check(f.media.get(0).starts==0,"cancel never opens mic");
    }}
    static void cancelAnswerRace()throws Exception{try(Fixture f=new Fixture()){
        SipMessage invite=f.dial();f.send(f.response(invite,180,"Ringing","",""));await(()->f.state.equals("ringing"),"ringing before cancel race");f.sip.hangup();f.receive("CANCEL");f.send(f.response(invite,200,"OK","",sdp()));f.receive("ACK");f.receive("BYE");await(()->f.state.equals("idle"),"late acceptance ended with BYE");check(f.media.get(0).starts==0,"cancel/200 race does not open mic");
    }}
    static void rejection()throws Exception{try(Fixture f=new Fixture()){SipMessage invite=f.dial();f.send(f.response(invite,486,"Busy Here","",""));f.receive("ACK");await(()->f.state.equals("idle"),"busy releases dialog");check(f.media.get(0).starts==0,"busy does not start audio");}}
    static String incoming(Fixture f,String method,int seq,String to,String body){return method+" sip:100@127.0.0.1 SIP/2.0\r\nVia: SIP/2.0/UDP 127.0.0.1:"+f.pbx.getLocalPort()+";branch=z9hG4bK-incoming\r\nFrom: <sip:caller@127.0.0.1>;tag=caller\r\nTo: "+to+"\r\nCall-ID: inbound-test\r\nCSeq: "+seq+" "+method+"\r\nContact: <sip:asterisk@127.0.0.1:"+f.pbx.getLocalPort()+">\r\nContent-Length: "+body.getBytes(StandardCharsets.UTF_8).length+"\r\n\r\n"+body;}
    static void incoming()throws Exception{try(Fixture f=new Fixture()){
        f.send(incoming(f,"INVITE",10,"<sip:100@127.0.0.1>",sdp()));SipMessage ringing=f.receive("180");await(()->f.state.equals("incoming"),"incoming stays explicit");check(f.media.isEmpty(),"incoming never opens audio automatically");f.sip.answer();SipMessage ok=f.receive("200");check(f.media.get(0).starts==0,"incoming waits for ACK");f.send(incoming(f,"ACK",10,ok.header("to"),""));await(()->f.state.equals("connected"),"incoming accepted");check(f.media.get(0).starts==1,"incoming audio starts");f.send(incoming(f,"BYE",11,ok.header("to"),""));f.receive("200");await(()->f.state.equals("idle"),"remote BYE updates UI");check(f.media.get(0).closed>0,"remote BYE releases mic");
    }}
    static void stopActive()throws Exception{try(Fixture f=new Fixture()){SipMessage invite=f.dial();f.send(f.response(invite,200,"OK","",sdp()));f.receive("ACK");await(()->f.state.equals("connected"),"call ready before stop");f.sip.stop();f.receive("BYE");check(f.media.get(0).closed>0,"plugin stop frees media");check(!f.sip.registered(),"plugin stop unregisters locally");}}
    static void spoofedResponse()throws Exception{try(Fixture f=new Fixture()){SipMessage invite=f.dial();try(DatagramSocket foreign=new DatagramSocket(0)){byte[] fake=f.response(invite,200,"OK","",sdp()).getBytes(StandardCharsets.UTF_8);foreign.send(new DatagramPacket(fake,fake.length,f.peer));}Thread.sleep(200);check(f.media.get(0).starts==0,"foreign SIP peer cannot answer dialog");f.send(f.response(invite,486,"Busy Here","",""));f.receive("ACK");}}
    static void retransmission()throws Exception{try(Fixture f=new Fixture()){
        SipMessage invite=f.dial();SipMessage repeated=f.receive("INVITE");check(invite.header("via").equals(repeated.header("via")),"UDP retry preserves INVITE transaction");check(invite.header("call-id").equals(repeated.header("call-id")),"UDP retry preserves dialog");
        f.send(f.response(invite,200,"OK","",sdp()));f.receive("ACK");await(()->f.state.equals("connected"),"connected after packet loss");f.sip.hangup();SipMessage bye=f.receive("BYE");SipMessage retry=f.receive("BYE");check(bye.header("via").equals(retry.header("via")),"lost BYE response retries same transaction");f.send(f.response(bye,200,"OK","",""));
    }}
    static void lateAnswerAfterCancel()throws Exception{try(Fixture f=new Fixture()){
        SipMessage old=f.dial();f.send(f.response(old,180,"Ringing","",""));await(()->f.state.equals("ringing"),"old call rings");f.sip.hangup();f.receive("CANCEL");f.send(f.response(old,487,"Request Terminated","",""));f.receive("ACK");await(()->f.state.equals("idle"),"old cancellation completes");
        SipMessage fresh=f.dial();f.send(f.response(old,200,"OK","",sdp()));SipMessage ack=f.receive("ACK");check(ack.header("call-id").equals(old.header("call-id")),"late old acceptance gets ACK");SipMessage bye=f.receive("BYE");check(bye.header("call-id").equals(old.header("call-id")),"late old acceptance gets BYE");check(f.media.get(0).starts==0,"old cancelled media stays shut");check(f.media.get(1).starts==0,"new media unaffected by old answer");f.send(f.response(fresh,486,"Busy Here","",""));f.receive("ACK");
    }}
    static void incomingDeclineRetransmission()throws Exception{try(Fixture f=new Fixture()){
        String invite=incoming(f,"INVITE",10,"<sip:100@127.0.0.1>",sdp());f.send(invite);f.receive("180");f.sip.hangup();f.receive("603");await(()->f.state.equals("idle"),"decline idle");f.send(invite);f.receive("603");check(f.media.isEmpty(),"retransmitted declined call does not ring or open mic");
    }}
    static void mediaFailure()throws Exception{try(Fixture f=new Fixture()){SipMessage invite=f.dial();f.send(f.response(invite,200,"OK","",sdp()));f.receive("ACK");await(()->f.state.equals("connected"),"connected before capture loss");f.media.get(0).healthy=false;f.receive("BYE");await(()->f.state.equals("error"),"audio failure ends dialog and reports error");check(f.media.get(0).closed>0,"capture loss frees media");}}
    static void codecs()throws Exception{
        check(AndroidG711.parseOffer(sdp()).payload==0,"SDP PCMU negotiation");check(AndroidG711.parseOffer(sdp().replace("RTP/AVP 0","RTP/AVP 8")).payload==8,"SDP PCMA negotiation");
        boolean rejected=false;try{AndroidG711.parseOffer(sdp().replace("RTP/AVP","RTP/SAVP"));}catch(IllegalArgumentException e){rejected=true;}check(rejected,"unsupported encrypted RTP rejected");
        check(Math.abs(AndroidG711.muToLinear(AndroidG711.linearToMu((short)1000))-1000)<50,"mu-law audio conversion");check(Math.abs(AndroidG711.aToLinear(AndroidG711.linearToA((short)1000))-1000)<50,"A-law audio conversion");
        check((AndroidG711.linearToA((short)1000)&255)==0xfa,"A-law positive reference vector");check((AndroidG711.linearToA((short)-1000)&255)==0x7a,"A-law negative reference vector");check((AndroidG711.linearToA((short)0)&255)==0xd5,"A-law silence reference vector");
        DialerModel m=new DialerModel();m.plus();m.digit("4");m.digit("9");m.digit("1");check(m.number.equals("+491"),"native plus prefix");
    }
    static void independentDevices()throws Exception{try(Fixture first=new Fixture("101");Fixture second=new Fixture("102")){
        check(first.sip.registered()&&second.sip.registered(),"two device clients registered simultaneously");first.sip.dial("102");SipMessage a=first.receive("INVITE");second.sip.dial("101");SipMessage b=second.receive("INVITE");check(a.header("from").contains("sip:101@"),"first device uses own identity");check(b.header("from").contains("sip:102@"),"second device uses own identity");check(a.header("contact").contains("sip:101@"),"first contact separated");check(b.header("contact").contains("sip:102@"),"second contact separated");check(!a.header("call-id").equals(b.header("call-id")),"devices have isolated dialogs");first.send(first.response(a,486,"Busy Here","",""));second.send(second.response(b,486,"Busy Here","",""));first.receive("ACK");second.receive("ACK");
    }}
}
