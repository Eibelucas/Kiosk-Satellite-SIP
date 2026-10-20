// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip.nativephone;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.*;
import java.net.*;
import java.util.Random;

/** Direct Android audio; no ActivityThread reflection or browser microphone.
 * G.711 conversion adapted from meiser79 SIP Phone (see NOTICE).
 * Audio focus is local Android focus, not KS's still-missing shared capture lease.
 */
final class AndroidG711 implements NativeSipClient.Media {
    static final class Offer {
        final InetAddress address;final int port,payload;
        Offer(InetAddress a,int p,int pt){address=a;port=p;payload=pt;}
    }
    private final Context context;
    private final InetAddress local;
    private final DatagramSocket rtp;
    private volatile Offer remote;
    private volatile boolean running,muted,closed;
    private AudioRecord recorder;
    private AudioTrack track;
    private AudioManager manager;
    private final RtpPlayoutQueue playout=new RtpPlayoutQueue();
    private boolean focus,modeChanged,oldSpeaker;
    private int oldMode;
    private final AudioManager.OnAudioFocusChangeListener focusChanges=change->{if(change<0)close();};
    private final Random random=new Random();
    private int sequence=random.nextInt(65536),timestamp=random.nextInt();
    private final int ssrc=random.nextInt();

    AndroidG711(InetAddress local,Context context)throws Exception{
        if(context==null)throw new IllegalStateException("Dialer not ready");
        this.local=local;this.context=context.getApplicationContext();
        rtp=new DatagramSocket(new InetSocketAddress(local,0));rtp.setSoTimeout(200);
    }
    static Offer parseOffer(String sdp)throws Exception{
        if(sdp==null||sdp.isEmpty())throw new IllegalArgumentException("Missing SDP");
        String ip=null;int port=-1,payload=-1;boolean audio=false;
        for(String raw:sdp.split("\\r?\\n")){
            String line=raw.trim();
            if(line.startsWith("c=IN IP4 "))ip=line.substring(9).trim();
            else if(line.startsWith("m=audio ")){
                String[] fields=line.substring(8).trim().split(" +");
                if(fields.length<3||!fields[1].equals("RTP/AVP"))throw new IllegalArgumentException("Unsupported transport");
                port=Integer.parseInt(fields[0]);audio=true;
                for(int i=2;i<fields.length;i++)if(fields[i].equals("0")||fields[i].equals("8")){payload=Integer.parseInt(fields[i]);break;}
            }else if(line.startsWith("m=")&&audio)break;
        }
        if(ip==null||!ip.matches("[0-9.]{7,15}")||port<1||port>65535||payload<0)throw new IllegalArgumentException("Invalid G.711 SDP");
        return new Offer(InetAddress.getByName(ip),port,payload);
    }
    private String sdp(String payloads){return "v=0\r\no=- "+Integer.toUnsignedString(ssrc)+" 1 IN IP4 "+local.getHostAddress()+"\r\ns=Native SIP Lab\r\nc=IN IP4 "+local.getHostAddress()+"\r\nt=0 0\r\nm=audio "+rtp.getLocalPort()+" RTP/AVP "+payloads+"\r\na=rtpmap:0 PCMU/8000\r\na=rtpmap:8 PCMA/8000\r\na=ptime:20\r\na=sendrecv\r\n";}
    public String offer(){return sdp("0 8");}
    private void negotiate(String sdp)throws Exception{remote=parseOffer(sdp);if(!remote.address.equals(local)&&!remote.address.isSiteLocalAddress())throw new IllegalArgumentException("Only LAN RTP is supported");}
    public String answer(String sdp)throws Exception{negotiate(sdp);return sdp(String.valueOf(remote.payload));}
    public boolean healthy(){return !closed;}
    public void mute(boolean value){muted=value;}
    public synchronized void start(String sdp)throws Exception{
        if(closed)throw new IllegalStateException("Media already closed");
        if(running)return;
        negotiate(sdp);
        if(context.checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)throw new IllegalStateException("Microphone permission missing");
        manager=(AudioManager)context.getSystemService(Context.AUDIO_SERVICE);
        if(manager==null)throw new IllegalStateException("Audio service missing");
        try{
            focus=manager.requestAudioFocus(focusChanges,AudioManager.STREAM_VOICE_CALL,AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)==AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
            if(!focus)throw new IllegalStateException("Audio focus denied");
            oldMode=manager.getMode();oldSpeaker=manager.isSpeakerphoneOn();modeChanged=true;
            manager.setMode(AudioManager.MODE_IN_COMMUNICATION);manager.setSpeakerphoneOn(true);
            int input=AudioRecord.getMinBufferSize(8000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);
            int output=AudioTrack.getMinBufferSize(8000,AudioFormat.CHANNEL_OUT_MONO,AudioFormat.ENCODING_PCM_16BIT);
            if(input<=0||output<=0)throw new IllegalStateException("8 kHz audio unavailable");
            recorder=new AudioRecord(MediaRecorder.AudioSource.VOICE_COMMUNICATION,8000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,Math.max(input,640));
            AudioTrack.Builder builder=new AudioTrack.Builder()
                    .setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
                    .setAudioFormat(new AudioFormat.Builder().setSampleRate(8000).setChannelMask(AudioFormat.CHANNEL_OUT_MONO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
                    .setBufferSizeInBytes(Math.max(output,640)).setTransferMode(AudioTrack.MODE_STREAM);
            if(android.os.Build.VERSION.SDK_INT>=26)builder.setPerformanceMode(AudioTrack.PERFORMANCE_MODE_LOW_LATENCY);
            track=builder.build();
            if(recorder.getState()!=AudioRecord.STATE_INITIALIZED||track.getState()!=AudioTrack.STATE_INITIALIZED)throw new IllegalStateException("Audio not initialized");
            track.setBufferSizeInFrames(320); // Request 40 ms; Android may enforce a higher minimum.
            recorder.startRecording();track.play();
            if(recorder.getRecordingState()!=AudioRecord.RECORDSTATE_RECORDING)throw new IllegalStateException("Microphone not recording");
            running=true;Thread tx=new Thread(this::sendLoop,"native-rtp-tx"),rx=new Thread(this::receiveLoop,"native-rtp-rx"),speaker=new Thread(this::playLoop,"native-rtp-speaker");tx.setDaemon(true);rx.setDaemon(true);speaker.setDaemon(true);tx.start();rx.start();speaker.start();
        }catch(Exception error){close();throw error;}
    }
    public synchronized void close(){
        if(closed)return;closed=true;running=false;rtp.close();playout.close();
        if(recorder!=null){try{recorder.stop();}catch(Exception ignored){}recorder.release();recorder=null;}
        if(track!=null){try{track.stop();}catch(Exception ignored){}track.release();track=null;}
        if(manager!=null){if(modeChanged){manager.setSpeakerphoneOn(oldSpeaker);manager.setMode(oldMode);}if(focus)manager.abandonAudioFocus(focusChanges);}
    }
    private void sendLoop(){
        android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_AUDIO);
        byte[] pcm=new byte[320],wire=new byte[172];
        try{AudioRecord capture=recorder;while(running){
            int count=capture.read(pcm,0,pcm.length);if(count<0)throw new IllegalStateException("Microphone lost");if(count<2)continue;int samples=count/2;
            wire[0]=(byte)0x80;wire[1]=(byte)remote.payload;wire[2]=(byte)(sequence>>>8);wire[3]=(byte)sequence;sequence=(sequence+1)&65535;
            wire[4]=(byte)(timestamp>>>24);wire[5]=(byte)(timestamp>>>16);wire[6]=(byte)(timestamp>>>8);wire[7]=(byte)timestamp;timestamp+=samples;
            wire[8]=(byte)(ssrc>>>24);wire[9]=(byte)(ssrc>>>16);wire[10]=(byte)(ssrc>>>8);wire[11]=(byte)ssrc;
            for(int i=0;i<samples;i++){short value=muted?0:(short)((pcm[i*2]&255)|((pcm[i*2+1]&255)<<8));wire[12+i]=remote.payload==0?linearToMu(value):linearToA(value);}
            rtp.send(new DatagramPacket(wire,12+samples,remote.address,remote.port));
        }}catch(Exception ignored){close();}
    }
    private void receiveLoop(){
        android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_AUDIO);
        byte[] bytes=new byte[2048];
        try{while(running){
            DatagramPacket p=new DatagramPacket(bytes,bytes.length);try{rtp.receive(p);}catch(SocketTimeoutException ignored){continue;}
            if(!p.getAddress().equals(remote.address)||p.getPort()!=remote.port||p.getLength()<13||(bytes[0]&0xc0)!=0x80||(bytes[1]&0x7f)!=remote.payload)continue;
            int header=12+4*(bytes[0]&15),size=p.getLength();
            if((bytes[0]&0x10)!=0){if(size<header+4)continue;header+=4+4*((bytes[header+2]&255)*256+(bytes[header+3]&255));}
            if((bytes[0]&0x20)!=0){int padding=bytes[size-1]&255;if(padding<1||padding>size-header)continue;size-=padding;}
            if(size<=header||size-header>RtpPlayoutQueue.MAX_SAMPLES)continue;
            byte[] pcm=new byte[(size-header)*2];for(int i=header;i<size;i++){short value=remote.payload==0?muToLinear(bytes[i]):aToLinear(bytes[i]);int at=(i-header)*2;pcm[at]=(byte)value;pcm[at+1]=(byte)(value>>>8);}
            int sequence=((bytes[2]&255)<<8)|(bytes[3]&255);
            long source=((long)(bytes[8]&255)<<24)|((long)(bytes[9]&255)<<16)|((long)(bytes[10]&255)<<8)|(bytes[11]&255);
            playout.offer(sequence,source,pcm);
        }}catch(Exception ignored){close();}
    }
    private void playLoop(){
        android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_AUDIO);
        try{AudioTrack playback=track;while(running){
            byte[] pcm=playout.take();if(pcm==null)break;
            int at=0;while(running&&at<pcm.length){int count=playback.write(pcm,at,pcm.length-at);if(count<=0)throw new IllegalStateException("Speaker lost");at+=count;}
        }}catch(Exception ignored){close();}
    }
    static byte linearToMu(short sample){int x=sample;int sign=(x>>8)&0x80;if(sign!=0)x=-x;if(x>32635)x=32635;x+=0x84;int exponent=7;for(int mask=0x4000;(x&mask)==0&&exponent>0;mask>>=1)exponent--;int mantissa=(x>>(exponent+3))&0x0f;return(byte)~(sign|(exponent<<4)|mantissa);}
    static short muToLinear(byte value){int u=(~value)&255;int t=((u&15)<<3)+0x84;t<<=(u&0x70)>>4;return(short)(((u&0x80)!=0)?(0x84-t):(t-0x84));}
    static byte linearToA(short sample){int x=sample;int mask;if(x>=0)mask=0xd5;else{mask=0x55;x=-x-1;}if(x>32767)x=32767;int seg=0;if(x>=256){seg=1;int v=x>>8;while(v>1&&seg<7){v>>=1;seg++;}}int aval=seg<<4;if(seg<2)aval|=(x>>4)&15;else aval|=(x>>(seg+3))&15;return(byte)(aval^mask);}
    static short aToLinear(byte value){int a=(value&255)^0x55;int t=(a&15)<<4;int seg=(a&0x70)>>4;if(seg==0)t+=8;else if(seg==1)t+=0x108;else{t+=0x108;t<<=seg-1;}return(short)(((a&0x80)!=0)?t:-t);}
}
