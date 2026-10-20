// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip.nativephone;

import java.util.ArrayDeque;

/** Bounded live PCM: a stalled speaker must not make the conversation drift behind. */
final class RtpPlayoutQueue {
    static final int MAX_SAMPLES=480; // 60 ms at 8 kHz, including variable packet sizes.
    private final ArrayDeque<byte[]> frames=new ArrayDeque<>();
    private int samples,lastSequence;
    private long source;
    private boolean haveSequence,closed;

    synchronized void offer(int sequence,long ssrc,byte[] pcm){
        if(closed||pcm.length==0||pcm.length%2!=0||pcm.length/2>MAX_SAMPLES)return;
        if(haveSequence&&source==ssrc){
            int delta=(sequence-lastSequence)&65535;
            if(delta==0||delta>=32768)return; // Duplicate/late audio should never be replayed.
        }else{frames.clear();samples=0;}
        source=ssrc;lastSequence=sequence;haveSequence=true;
        int count=pcm.length/2;
        while(samples+count>MAX_SAMPLES)samples-=frames.removeFirst().length/2;
        frames.addLast(pcm);samples+=count;notifyAll();
    }
    synchronized byte[] take()throws InterruptedException{
        while(!closed&&frames.isEmpty())wait();
        if(closed)return null;
        byte[] pcm=frames.removeFirst();samples-=pcm.length/2;return pcm;
    }
    synchronized int queuedSamples(){return samples;}
    synchronized void close(){closed=true;frames.clear();samples=0;notifyAll();}
}
