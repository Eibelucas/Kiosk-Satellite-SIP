// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip.nativephone;

import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.*;
import java.util.concurrent.ConcurrentLinkedQueue;

/** Experimental single-dialog SIP endpoint per kiosk for a directly attached LAN Asterisk.
 * The worker owns SIP, timers and media. UI commands only enqueue work.
 * No AMI Originate, intercom invitation or auto-answer setting is involved.
 */
public final class NativeSipClient {
    public interface Events {
        void registration(boolean ready);
        void call(String state, String peer, String detail);
    }
    public interface Media {
        String offer();
        String answer(String remoteSdp) throws Exception;
        void start(String remoteSdp) throws Exception;
        void mute(boolean on);
        void close();
        default boolean healthy(){return true;}
    }
    public interface MediaFactory { Media open(InetAddress local) throws Exception; }
    public static final class Config {
        public final String server, user, password;
        public final int port, localPort;
        public Config(String server, int port, String password, int localPort) {
            this(server,port,"100",password,localPort);
        }
        public Config(String server, int port, String user, String password, int localPort) {
            if(user==null||!user.matches("1[0-9]{2}"))throw new IllegalArgumentException("Nebenstelle von 100 bis 199 eingeben.");
            if (server == null || !server.matches("[a-zA-Z0-9.-]{1,253}") || server.startsWith("-") ||
                    port < 1 || port > 65535 || localPort < 1024 || localPort > 65535 ||
                    password == null || password.length() < 8 || password.length() > 256 ||
                    password.matches("(?s).*[\\p{Cntrl}].*")) throw new IllegalArgumentException("SIP-Adresse, Ports und Geräte-SIP-Passwort prüfen.");
            this.server=server; this.user=user; this.port=port; this.password=password; this.localPort=localPort;
        }
    }
    private static final class Dialog {
        String id, from, to, uri, branch, lastRequest, ack;
        int seq=1;
        boolean outgoing, established, cancel, provisional, cancelSent, started, authorized;
        long deadline, retryAt, interval=500;
        Media media;
        SipMessage invite;
    }
    private static final class Transaction {
        String request,id,method,branch;
        int seq;
        long next,until,interval=500;
    }
    private final Config cfg;
    private final Events events;
    private final MediaFactory factory;
    private final SecureRandom random=new SecureRandom();
    private final Queue<Runnable> commands=new ConcurrentLinkedQueue<>();
    private volatile boolean running, registered;
    private volatile DatagramSocket socket;
    private Thread worker;
    private InetAddress pbx, local;
    private InetSocketAddress target;
    private Dialog dialog;
    private String regId,regTag,regBranch,regRequest;
    private int regSeq;
    private boolean regAuthorized;
    private long registerAt,regRetryAt,regDeadline,regInterval;
    private String closedId,closedAck,closedFrom,closedTo;
    private final List<Transaction> pending=new ArrayList<>();
    private Dialog cancelled;
    private long cancelledUntil;
    private String finalIncomingId, finalIncomingResponse, finalIncomingBranch;
    private long finalIncomingUntil;
    private long closedUntil;

    public NativeSipClient(Config cfg, Events events, MediaFactory factory) { this.cfg=cfg;this.events=events;this.factory=factory; }
    public boolean registered() { return registered; }
    public void start() { if(running)return;running=true;worker=new Thread(this::run,"native-sip-lab");worker.setDaemon(true);worker.start(); }
    public void dial(String number) {
        if(number==null||!number.matches("\\+?[0-9*#]{3,20}"))throw new IllegalArgumentException("Nummer: 3 bis 20 Ziffern, optional +, * oder #.");
        if(!running||!registered)throw new IllegalStateException("Das Gerät ist noch nicht angemeldet.");
        commands.add(()->begin(number));
    }
    public void answer() { commands.add(this::accept); }
    public void hangup() { commands.add(this::end); }
    public void mute(boolean on) { commands.add(()->{if(dialog!=null&&dialog.media!=null)dialog.media.mute(on);}); }
    public void stop() {
        running=false;
        Thread current=worker;
        if(current!=null&&current!=Thread.currentThread()) { try {current.join(1800);}catch(InterruptedException e){Thread.currentThread().interrupt();} }
        DatagramSocket currentSocket=socket;if(currentSocket!=null)currentSocket.close();
    }
    private void run() {
        try {
            pbx=InetAddress.getByName(cfg.server);
            if(!(pbx instanceof Inet4Address))throw new IllegalArgumentException("Der Test unterstützt nur IPv4.");
            target=new InetSocketAddress(pbx,cfg.port);
            try(DatagramSocket probe=new DatagramSocket()){probe.connect(target);local=probe.getLocalAddress();}
            socket=new DatagramSocket(new InetSocketAddress(local,cfg.localPort));socket.setSoTimeout(100);
            regId=id();regTag=id();register(null);
            while(running) {
                Runnable action;while((action=commands.poll())!=null)action.run();
                timers();
                DatagramPacket packet=new DatagramPacket(new byte[16384],16384);
                try{socket.receive(packet);}catch(SocketTimeoutException ignored){continue;}
                // Asterisk is the only signalling peer, including for incoming calls.
                if(!pbx.equals(packet.getAddress())||packet.getPort()!=cfg.port)continue;
                SipMessage msg=SipMessage.parse(new String(packet.getData(),0,packet.getLength(),StandardCharsets.UTF_8));
                if(msg==null)continue;
                try { if(msg.isRequest())request(msg);else response(msg); }
                catch(Exception badMessage){finish("Anruf konnte nicht verarbeitet werden.");}
            }
        } catch(Exception e) { notifyCall("error","","SIP-Verbindung fehlgeschlagen. IP, Port, Passwort und Mikrofon prüfen."); }
        finally {
            if(dialog!=null){try{end();}catch(Exception ignored){}if(dialog!=null&&dialog.media!=null)dialog.media.close();dialog=null;}
            if(socket!=null){socket.close();socket=null;}registered=false;events.registration(false);commands.clear();
        }
    }
    private void timers() throws Exception {
        long now=System.nanoTime()/1_000_000;
        for(Iterator<Transaction> i=pending.iterator();i.hasNext();){Transaction t=i.next();if(now>=t.until){i.remove();continue;}if(now>=t.next){send(t.request);t.interval=Math.min(4000,t.interval*2);t.next=now+t.interval;}}
        if(now>=registerAt&&regRequest==null)register(null);
        if(regRequest!=null&&now>=regDeadline){regRequest=null;registered=false;events.registration(false);registerAt=now+5000;}
        else if(regRequest!=null&&now>=regRetryAt){send(regRequest);regInterval=Math.min(4000,regInterval*2);regRetryAt=now+regInterval;}
        Dialog d=dialog;
        if(d==null)return;
        if(d.established){if(d.media!=null&&!d.media.healthy()){end();notifyCall("error","","Audio unterbrochen. Gespräch beendet.");}return;}
        if(now>=d.deadline){if(d.outgoing){d.cancel=true;if(d.provisional)sendCancel(d);}else send(reply(d.invite,480,"Temporarily Unavailable",d.to,""));finish("Keine Antwort / Zeitüberschreitung.");return;}
        if(d.outgoing&&!d.provisional&&now>=d.retryAt){send(d.lastRequest);d.interval=Math.min(4000,d.interval*2);d.retryAt=now+d.interval;}
        if(!d.outgoing&&d.started&&now>=d.retryAt){send(d.lastRequest);d.interval=Math.min(4000,d.interval*2);d.retryAt=now+d.interval;}
    }
    private void register(SipMessage challenge) throws Exception {
        regSeq++;regBranch=branch();String uri="sip:"+cfg.server;
        String auth=challenge==null?"":auth(challenge,"REGISTER",uri);
        regAuthorized=challenge!=null;
        regRequest=headers("REGISTER",uri,regBranch,"<sip:"+cfg.user+"@"+cfg.server+">;tag="+regTag,"<sip:"+cfg.user+"@"+cfg.server+">",regId,regSeq)+
                "Expires: 120\r\n"+auth+"Content-Length: 0\r\n\r\n";
        long now=System.nanoTime()/1_000_000;regDeadline=now+8000;regInterval=500;regRetryAt=now+500;registerAt=now+60000;send(regRequest);
    }
    private void begin(String number) {
        if(dialog!=null){notifyCall("busy",number,"Es läuft bereits ein Anruf.");return;}
        if(!registered){notifyCall("error",number,"SIP nicht angemeldet.");return;}
        Dialog d=new Dialog();d.outgoing=true;d.id=id();d.from="<sip:"+cfg.user+"@"+cfg.server+">;tag="+id();
        // # is escaped in a SIP URI; Asterisk decodes the destination user.
        d.uri="sip:"+number.replace("#","%23")+"@"+cfg.server;d.to="<"+d.uri+">";d.branch=branch();
        dialog=d;
        try{d.media=factory.open(local);invite(d,null);notifyCall("calling",number,"Verbindet …");}
        catch(Exception e){finish("Audio konnte nicht vorbereitet werden. Mikrofonberechtigung prüfen.");}
    }
    private void invite(Dialog d,SipMessage challenge) throws Exception {
        String sdp=d.media.offer();String auth=challenge==null?"":auth(challenge,"INVITE",d.uri);
        d.lastRequest=headers("INVITE",d.uri,d.branch,d.from,d.to,d.id,d.seq)+auth+body(sdp);
        long now=System.nanoTime()/1_000_000;d.deadline=now+32000;d.retryAt=now+500;d.interval=500;d.provisional=false;send(d.lastRequest);
    }
    private void response(SipMessage m) throws Exception {
        if(m.status()>=200)pending.removeIf(t->t.id.equals(m.header("call-id"))&&t.method.equals(m.cseqMethod())&&t.seq==m.cseqNumber()&&viaMatches(m,t.branch));
        if("REGISTER".equals(m.cseqMethod())&&regId.equals(m.header("call-id"))&&m.cseqNumber()==regSeq&&viaMatches(m,regBranch)){
            if(m.status()<200)return;
            regRequest=null;
            if((m.status()==401||m.status()==407)&&!regAuthorized){register(m);return;}
            registered=m.status()==200;events.registration(registered);registerAt=System.nanoTime()/1_000_000+(registered?60000:5000);return;
        }
        Dialog d=dialog;
        // A timed-out/cancelled INVITE may still be accepted while another call is starting.
        if(cancelled!=null&&cancelled.id.equals(m.header("call-id"))&&"INVITE".equals(m.cseqMethod())&&m.cseqNumber()==cancelled.seq&&viaMatches(m,cancelled.branch)&&System.nanoTime()/1_000_000<cancelledUntil&&m.status()>=200){
            Dialog old=cancelled;
            if(m.status()==200){String uri=contact(m.header("contact"));if(uri==null)return;String to=m.header("to");send(headers("ACK",uri,branch(),old.from,to,old.id,old.seq)+"Content-Length: 0\r\n\r\n");queue(headers("BYE",uri,branch(),old.from,to,old.id,old.seq+1)+"Content-Length: 0\r\n\r\n");}
            else send(headers("ACK",old.uri,old.branch,old.from,m.header("to"),old.id,old.seq)+"Content-Length: 0\r\n\r\n");
            return;
        }
        if(d==null){if(closedId!=null&&closedId.equals(m.header("call-id"))&&"INVITE".equals(m.cseqMethod())&&m.status()==200&&System.nanoTime()/1_000_000<closedUntil&&closedAck!=null)send(closedAck);return;}
        if(!d.outgoing||!d.id.equals(m.header("call-id"))||!"INVITE".equals(m.cseqMethod())||m.cseqNumber()!=d.seq||!viaMatches(m,d.branch))return;
        int code=m.status();if(code<100)return;
        if(code<200){d.provisional=true;if(code>=180&&!d.cancel)notifyCall("ringing","","Klingelt beim Ziel …");if(d.cancel)sendCancel(d);return;}
        String to=m.header("to");if(to==null)return;
        if(code>=300){send(headers("ACK",d.uri,d.branch,d.from,to,d.id,d.seq)+"Content-Length: 0\r\n\r\n");
            if((code==401||code==407)&&!d.authorized&&!d.cancel){d.authorized=true;d.seq++;d.branch=branch();invite(d,m);return;}
            finish(d.cancel?"Anruf abgebrochen.":"Anruf beendet: SIP "+code);return;
        }
        if(code!=200)return;
        String remoteUri=contact(m.header("contact"));
        if(remoteUri==null){finish("Ungültiges SIP-Ziel.");return;}
        // Direct Asterisk dialog only. A proxy route set is outside this lab's scope.
        if(!m.all("record-route").isEmpty()){finish("SIP-Proxys mit Record-Route werden im Test nicht unterstützt.");return;}
        d.to=to;d.uri=remoteUri;d.ack=headers("ACK",d.uri,branch(),d.from,d.to,d.id,d.seq)+"Content-Length: 0\r\n\r\n";send(d.ack);
        if(d.established)return;
        d.established=true;
        if(d.cancel){end();return;}
        try{d.media.start(m.body);notifyCall("connected","","Verbunden");}
        catch(Exception e){end();notifyCall("error","","Audio nicht verfügbar. Mikrofon und Audio-Zugriff prüfen.");}
    }
    private void request(SipMessage m) throws Exception {
        for(String key:new String[]{"via","from","to","call-id","cseq"})if(m.header(key)==null)return;
        String method=m.method();Dialog d=dialog;boolean same=d!=null&&d.id.equals(m.header("call-id"));
        if("OPTIONS".equals(method)){send(reply(m,200,"OK",m.header("to"),""));return;}
        if("INVITE".equals(method)){
            if(finalIncomingId!=null&&finalIncomingId.equals(m.header("call-id"))&&viaMatches(m,finalIncomingBranch)&&System.nanoTime()/1_000_000<finalIncomingUntil){send(finalIncomingResponse);return;}
            if(same){if(!d.outgoing)send(d.lastRequest);else send(reply(m,488,"Not Acceptable Here",m.header("to"),""));return;}
            if(d!=null){send(reply(m,486,"Busy Here",m.header("to"),""));return;}
            d=new Dialog();d.id=m.header("call-id");d.invite=m;d.from=m.header("from");d.to=m.header("to")+";tag="+id();d.uri=contact(m.header("contact"));
            if(d.uri==null){send(reply(m,400,"Bad Request",d.to,""));return;}
            d.deadline=System.nanoTime()/1_000_000+45000;d.seq=m.cseqNumber();d.lastRequest=reply(m,180,"Ringing",d.to,"");dialog=d;send(d.lastRequest);
            notifyCall("incoming",SipMessage.caller(d.from),"Eingehender Anruf");return;
        }
        if("ACK".equals(method)){
            if(same&&!d.outgoing&&d.started&&!d.established&&m.cseqNumber()==d.seq&&dialogMatches(m,d)){
                try{d.media.start(d.invite.body);d.established=true;notifyCall("connected","","Verbunden");}catch(Exception e){d.established=true;end();}
            }return;
        }
        if("CANCEL".equals(method)&&same&&!d.outgoing&&!d.established&&m.cseqNumber()==d.seq){send(reply(m,200,"OK",d.to,""));send(reply(d.invite,487,"Request Terminated",d.to,""));finish("Anruf abgebrochen.");return;}
        if("BYE".equals(method)&&same&&d.established&&dialogMatches(m,d)){send(reply(m,200,"OK",m.header("to"),""));finish("Gespräch beendet.");return;}
        if("BYE".equals(method)&&d==null&&closedId!=null&&closedId.equals(m.header("call-id"))&&System.nanoTime()/1_000_000<closedUntil){send(reply(m,200,"OK",m.header("to"),""));return;}
        send(reply(m,481,"Call/Transaction Does Not Exist",m.header("to"),""));
    }
    private void accept(){Dialog d=dialog;if(d==null||d.outgoing||d.started)return;try{
        d.media=factory.open(local);String sdp=d.media.answer(d.invite.body);d.started=true;d.lastRequest=reply(d.invite,200,"OK",d.to,sdp);
        long now=System.nanoTime()/1_000_000;d.deadline=now+8000;d.retryAt=now+500;send(d.lastRequest);
    }catch(Exception e){try{send(reply(d.invite,488,"Not Acceptable Here",d.to,""));}catch(Exception ignored){}finish("Audio nicht verfügbar.");}}
    private void end(){Dialog d=dialog;if(d==null)return;try{
        if(d.established){String from=d.outgoing?d.from:d.to,to=d.outgoing?d.to:d.from;queue(headers("BYE",d.uri,branch(),from,to,d.id,++d.seq)+"Content-Length: 0\r\n\r\n");finish("Gespräch beendet.");}
        else if(d.outgoing){d.cancel=true;if(d.provisional)sendCancel(d);if(d.media!=null)d.media.close();notifyCall("cancelling","","Wird abgebrochen …");}
        else {d.lastRequest=reply(d.invite,603,"Decline",d.to,"");rememberIncoming(d,d.lastRequest);send(d.lastRequest);finish("Anruf abgelehnt.");}
    }catch(Exception e){finish("Verbindung beendet.");}}
    private void sendCancel(Dialog d)throws Exception {if(d.cancelSent)return;d.cancelSent=true;queue(headers("CANCEL",d.uri,d.branch,d.from,d.to,d.id,d.seq)+"Content-Length: 0\r\n\r\n");}
    private void rememberIncoming(Dialog d,String response){finalIncomingId=d.id;finalIncomingResponse=response;String via=d.invite.header("via");int at=via.indexOf("branch=");finalIncomingBranch=at<0?"":via.substring(at+7).split("[;\\s]",2)[0];finalIncomingUntil=System.nanoTime()/1_000_000+32000;}
    private void queue(String request)throws Exception {SipMessage m=SipMessage.parse(request);Transaction t=new Transaction();t.request=request;t.id=m.header("call-id");t.method=m.method();t.seq=m.cseqNumber();String via=m.header("via");t.branch=via.substring(via.indexOf("branch=")+7).split(";",2)[0];long now=System.nanoTime()/1_000_000;t.next=now+500;t.until=now+32000;if(pending.size()<16)pending.add(t);send(request);}
    private void finish(String detail){Dialog old=dialog;dialog=null;if(old!=null){if(old.outgoing&&old.cancel&&!old.established){cancelled=old;cancelledUntil=System.nanoTime()/1_000_000+64000;}if(old.media!=null)old.media.close();closedId=old.id;closedAck=old.ack;closedFrom=old.from;closedTo=old.to;closedUntil=System.nanoTime()/1_000_000+32000;}notifyCall("idle","",detail);}
    private void notifyCall(String state,String peer,String detail){try{events.call(state,peer,detail);}catch(RuntimeException ignored){}}
    private boolean viaMatches(SipMessage m,String value){String via=m.header("via");if(via==null||value==null)return false;int at=via.indexOf("branch=");return at>=0&&via.substring(at+7).split("[;\\s]",2)[0].equals(value);}
    private boolean dialogMatches(SipMessage m,Dialog d){String from=d.outgoing?d.to:d.from,to=d.outgoing?d.from:d.to;return tag(from).equals(tag(m.header("from")))&&tag(to).equals(tag(m.header("to")));}
    private String tag(String value){if(value==null)return "";int p=value.indexOf(";tag=");return p<0?"":value.substring(p+5).split("[;\\s]",2)[0];}
    private String contact(String value){if(value==null||value.indexOf('\r')>=0||value.indexOf('\n')>=0)return null;int a=value.indexOf('<'),b=value.indexOf('>');String uri=a>=0&&b>a?value.substring(a+1,b):value.split(";",2)[0].trim();return uri.matches("sip:[a-zA-Z0-9_.!~*'()%+@;=:-]+")?uri:null;}
    private String headers(String method,String uri,String branch,String from,String to,String id,int seq){return method+" "+uri+" SIP/2.0\r\nVia: SIP/2.0/UDP "+local.getHostAddress()+":"+cfg.localPort+";branch="+branch+";rport\r\nMax-Forwards: 70\r\nFrom: "+from+"\r\nTo: "+to+"\r\nCall-ID: "+id+"\r\nCSeq: "+seq+" "+method+"\r\nContact: <sip:"+cfg.user+"@"+local.getHostAddress()+":"+cfg.localPort+">\r\nAllow: INVITE, ACK, CANCEL, BYE, OPTIONS\r\nUser-Agent: Kiosk-SIP-Native-Lab\r\n";}
    private String reply(SipMessage m,int code,String reason,String to,String sdp){StringBuilder out=new StringBuilder("SIP/2.0 "+code+" "+reason+"\r\n");for(String via:m.all("via"))out.append("Via: ").append(via).append("\r\n");out.append("From: ").append(m.header("from")).append("\r\nTo: ").append(to).append("\r\nCall-ID: ").append(m.header("call-id")).append("\r\nCSeq: ").append(m.header("cseq")).append("\r\nContact: <sip:").append(cfg.user).append('@').append(local.getHostAddress()).append(':').append(cfg.localPort).append(">\r\n");return out+body(sdp);}
    private String body(String sdp){return (sdp.isEmpty()?"":"Content-Type: application/sdp\r\n")+"Content-Length: "+sdp.getBytes(StandardCharsets.UTF_8).length+"\r\n\r\n"+sdp;}
    private String auth(SipMessage challenge,String method,String uri){String value=challenge.header(challenge.status()==407?"proxy-authenticate":"www-authenticate");if(value==null||!value.startsWith("Digest "))throw new IllegalArgumentException("Digest challenge fehlt");Map<String,String> p=SipDigest.parseParams(value);String realm=p.get("realm"),nonce=p.get("nonce"),qop=null;if(realm==null||nonce==null||!p.getOrDefault("algorithm","MD5").equalsIgnoreCase("MD5"))throw new IllegalArgumentException("Nicht unterstützte SIP-Anmeldung");if(p.containsKey("qop")){for(String q:p.get("qop").split(","))if(q.trim().equals("auth"))qop="auth";if(qop==null)throw new IllegalArgumentException("qop nicht unterstützt");}String cnonce=id(),nc="00000001";String result=(challenge.status()==407?"Proxy-Authorization":"Authorization")+": Digest username=\""+cfg.user+"\", realm=\""+quote(realm)+"\", nonce=\""+quote(nonce)+"\", uri=\""+uri+"\", response=\""+SipDigest.response(cfg.user,realm,cfg.password,method,uri,nonce,qop,nc,cnonce)+"\", algorithm=MD5";if(qop!=null)result+=", qop=auth, nc="+nc+", cnonce=\""+cnonce+"\"";if(p.containsKey("opaque"))result+=", opaque=\""+quote(p.get("opaque"))+"\"";return result+"\r\n";}
    private String quote(String value){return value.replace("\\","\\\\").replace("\"","\\\"").replace("\r","").replace("\n","");}
    private void send(String message)throws Exception {byte[] bytes=message.getBytes(StandardCharsets.UTF_8);socket.send(new DatagramPacket(bytes,bytes.length,target));}
    private String id(){byte[] bytes=new byte[12];random.nextBytes(bytes);StringBuilder s=new StringBuilder();for(byte b:bytes)s.append(String.format("%02x",b&255));return s.toString();}
    private String branch(){return "z9hG4bK"+id();}
}
