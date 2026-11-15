#!/usr/bin/env python3
"""Inkborne / Tabula Rasa SFX + ambience generator.
Everything is synthesized here from numpy noise/oscillators. No samples.
Usage: python3 generate_sfx.py [outdir]   (renders WAV then MP3 via ffmpeg/libmp3lame)
"""
import sys, os, subprocess, numpy as np
from scipy import signal

SR = 44100
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..')
rng = np.random.default_rng(1999)

def t_(d): return np.arange(int(d*SR))/SR
def env(d, a=0.005, r=None, curve=4.0):
    t = t_(d); n = len(t)
    e = np.exp(-curve*t/d) if r is None else np.clip(1-(t-(d-r))/r, 0, 1)
    att = np.clip(t/max(a,1e-4), 0, 1)
    return e*att
def noise(d, seed=None):
    g = np.random.default_rng(seed) if seed is not None else rng
    return g.standard_normal(int(d*SR))
def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def lp(x, f, order=2):
    sos = signal.butter(order, f, 'lowpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def hp(x, f, order=2):
    sos = signal.butter(order, f, 'highpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def sine(f, d, ph=0):
    t = t_(d)
    if callable(f): return np.sin(2*np.pi*np.cumsum(f(t))/SR + ph)
    return np.sin(2*np.pi*f*t + ph)
def pad(x, d): 
    n = int(d*SR); return np.pad(x, (0, max(0, n-len(x))))[:n] if n > len(x) else x
def mix(*xs):
    n = max(len(x) for x in xs); o = np.zeros(n)
    for x in xs: o[:len(x)] += x
    return o
def at(x, sec, total):
    o = np.zeros(int(total*SR)); i = int(sec*SR); m = min(len(x), len(o)-i); o[i:i+m] += x[:m]; return o
def fade(x, fi=0.002, fo=0.01):
    x = x.copy(); a = int(fi*SR); b = int(fo*SR)
    if a: x[:a] *= np.linspace(0,1,a)
    if b: x[-b:] *= np.linspace(1,0,b)
    return x
def norm(x, db=-3.0):
    p = np.max(np.abs(x)) or 1; return x/p*10**(db/20)
def ks(f, d, damp=0.996, bright=0.5, seed=0):
    """Karplus-Strong pluck (koto-ish)."""
    n = int(d*SR); N = max(2, int(SR/f)); g = np.random.default_rng(seed)
    buf = lp(g.uniform(-1,1,N*4), 200+bright*6000)[-N:]
    out = np.zeros(n); b = buf.copy()
    for i in range(n):
        j = i % N; out[i] = b[j]; b[j] = damp*0.5*(b[j]+b[(j+1)%N])
    return out
def bell(f, d, ratios=(1, 2.76, 5.4, 8.93), decay=3.0):
    t = t_(d); o = np.zeros(len(t))
    for k, r in enumerate(ratios):
        o += np.sin(2*np.pi*f*r*t)*np.exp(-decay*(1+k*0.9)*t)/(k+1)
    return o*np.clip(t/0.002,0,1)
def woodblock(f, d=0.12):
    t = t_(d); return (np.sin(2*np.pi*f*t)+0.4*np.sin(2*np.pi*f*2.3*t))*np.exp(-t*45) + bp(noise(d),f,f*3)*np.exp(-t*120)*0.5
def thump(f0, d, drop=0.5):
    fr = lambda t: f0*(1-drop*np.clip(t/d,0,1)) 
    t = t_(d); return sine(fr, d)*np.exp(-t*6/d)
def brush(d, lo, hi, shape='swell', seed=None):
    x = bp(noise(d, seed), lo, hi); t = t_(d)
    e = np.sin(np.pi*t/d)**2 if shape=='swell' else np.exp(-5*t/d)
    return x*e
def write(name, x, stereo=False, db=-3.0, loop=False):
    if not loop: x = fade(x)
    x = norm(x, db) if db is not None else x
    wav = f'/tmp/{name}.wav'
    data = (np.clip(x,-1,1)*32767).astype(np.int16)
    import wave
    with wave.open(wav, 'wb') as w:
        w.setnchannels(2 if stereo else 1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((data.T.flatten() if stereo else data).tobytes() if not stereo else data.T.reshape(-1).tobytes())
    ch = ['-ac','2'] if stereo else ['-ac','1']
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',wav,*ch,'-c:a','libmp3lame','-q:a','2',os.path.join(OUT,f'{name}.mp3')], check=True)
    os.remove(wav)

# ---------------- SPEC keys: combat & menus ----------------
def s_step(seed):
    d=0.14; t=t_(d)
    return mix(lp(noise(d,seed),900)*np.exp(-t*35), 0.6*thump(110+seed*7,0.1,0.3))
def s_step_wood(seed):
    d=0.14; t=t_(d); return 0.8*woodblock(330+seed*15,d)+0.3*lp(noise(d,seed),2500)*np.exp(-t*60)
def s_move():
    d=0.06; t=t_(d); return bp(noise(d,7),2500,7000)*np.exp(-t*80)+0.5*sine(1800,d)*np.exp(-t*90)
def s_confirm():
    a = woodblock(880,0.12); b = bell(1320,0.5,decay=6)
    return mix(a, at(b,0.04,0.5))
def s_cancel():
    d=0.22; t=t_(d); sw = bp(noise(d,3),400,1600)*np.exp(-t*14)
    return mix(sw, 0.8*woodblock(330,0.15))
def s_ring():
    # closing-ring cue: soft rising breath + tick
    d=0.35; t=t_(d); br = bp(noise(d,11),1200,3500)*(t/d)**2
    return mix(br*0.6, at(woodblock(1200,0.08),0.3,d))
def s_hit(seed=0, heavy=False):
    d=0.4 if heavy else 0.22; t=t_(d)
    crack = hp(noise(d,seed),1500)*np.exp(-t*(30 if heavy else 50))
    body = thump(140 if heavy else 200, d, 0.6)
    swish = brush(0.12,1500,6000,'decay',seed+5)
    return mix(swish*0.5, at(crack*0.8+body*(1.3 if heavy else 0.8),0.03,d+0.03))
def s_clean():
    # perfect press: bright bell + pluck fifth
    b = bell(1046,0.7,decay=4); p = ks(784,0.6,0.997,0.8,1)*0.6
    return mix(woodblock(1500,0.08)*0.6, at(b,0.01,0.75), at(p,0.01,0.75))
def s_miss():
    d=0.35; t=t_(d)
    dull = sine(lambda t: 220-80*t/d, d)*np.exp(-t*10)
    return mix(dull, lp(noise(d,21),600)*np.exp(-t*25)*0.6)
def s_guard():
    d=0.8; g = bell(392,d,(1,2.0,3.01),decay=2.5)*0.6
    water = sum(sine(lambda t,f=f: f+300*np.exp(-t*20), 0.15)*np.exp(-t_(0.15)*25) for f in (900,1300))
    return mix(at(water,0,d), g, woodblock(260,0.15)*0.8)
def s_heal():
    notes=[523,659,784,1046]; d=1.2
    return mix(*[at(ks(f,0.9,0.998,0.6,i)*0.7,i*0.09,d) for i,f in enumerate(notes)], brush(d,3000,9000,'swell',4)*0.2)
def s_inkwing():
    d=2.4; t=t_(d)
    x = noise(d,31); fc = 300+3500*(t/d)**1.5
    # time-varying bandpass via short blocks
    out=np.zeros_like(x); B=1024
    for i in range(0,len(x),B):
        f=fc[i]; out[i:i+B]=bp(x[i:i+B+0],max(80,f*0.6),min(18000,f*1.6),1)
    out = lp(out,8000)
    trem = 0.6+0.4*np.sin(2*np.pi*(3+9*t/d)*t)
    swell = np.sin(np.pi*np.clip(t/d,0,1))**1.2
    drone = sine(lambda t: 55+55*(t/d), d)*0.5*swell
    flute = sine(lambda t: 440+220*(t/d)+6*np.sin(2*np.pi*5*t), d)*0.15*(t/d)**2*np.exp(-np.maximum(0,t-d*0.85)*20)
    boom = at(thump(70,1.0,0.5)*1.2,d-0.6,d+0.6)
    return mix(out*trem*swell, drone, flute, boom)
def s_seal():
    # stamp of a red seal: wood thunk + bell
    return mix(thump(160,0.25,0.4), woodblock(600,0.12)*0.7, at(bell(880,0.6,decay=5)*0.5,0.02,0.65))
def s_coin():
    d=0.7
    return mix(*[at(bell(f,0.5,(1,2.7,5.1),decay=7)*a,o,d) for f,o,a in ((2093,0,0.8),(2637,0.07,0.9),(3136,0.13,0.7))])
def s_text():
    d=0.04; t=t_(d); return bp(noise(d,41),1800,4000)*np.exp(-t*120)+0.3*sine(1200,d)*np.exp(-t*100)
def s_wipe():
    return brush(0.6,600,5000,'swell',51)+0.4*brush(0.6,150,600,'swell',52)
def s_combo_finish():
    d=1.0; return mix(s_hit(9,True)*0.8, at(bell(784,0.9,decay=3),0.08,d), at(ks(523,0.8,0.998,0.7,3)*0.6,0.08,d))
# ---------------- ambient keys ----------------
def s_enemy_hit():
    return s_hit(61)*0.9
def s_enemy_defeat():
    d=1.6; t=t_(d)
    disperse = bp(noise(d,71),400,6000)*np.exp(-t*2.5)*(0.5+0.5*np.sin(2*np.pi*14*t))
    fall = sine(lambda t: 300*np.exp(-t*1.5), d)*np.exp(-t*3)*0.4
    return mix(thump(90,0.5,0.5), disperse*0.7, fall, at(bell(523,1.3,decay=2.5)*0.3,0.15,d))
def s_lantern():
    d=1.5; t=t_(d); fl = lp(noise(d,81),400)*(0.5+0.5*np.abs(np.sin(2*np.pi*3*t)))
    return mix(fl*0.5, at(woodblock(220,0.15)*0.3,0.0,d))*np.sin(np.pi*t/d)
def s_wind():
    return wind_bed(6.0, 91)[0]

# ---------------- loops ----------------
def loopify(x, xf=2.0):
    """Make seamless: crossfade tail into head, return length-xf signal."""
    n=int(xf*SR); a=x[:n]; b=x[-n:]; w=np.linspace(0,1,n)
    head = a*w + b*(1-w)  # equal-ish power alternative
    return np.concatenate([head, x[n:-n]])
def wind_bed(d, seed):
    t=t_(d); g=np.random.default_rng(seed)
    gust = lp(g.standard_normal(len(t)),0.4,1); gust = 0.5+0.5*gust/np.max(np.abs(gust))
    w = bp(noise(d,seed+1),200,1200)*gust + 0.3*bp(noise(d,seed+2),1500,4000)*gust**2
    return w, gust
def bird(f0, d, seed):
    t=t_(d); g=np.random.default_rng(seed)
    chirps=np.zeros(len(t)); n=g.integers(2,5); cd=0.09
    for k in range(n):
        ct=t_(cd); fm=f0*(1+0.25*np.sin(np.pi*ct/cd))*(1+0.1*k)
        c=sine(lambda tt: f0*(1+0.3*np.sin(np.pi*tt/cd))*(1+0.08*k), cd)*np.sin(np.pi*ct/cd)**2
        i=int(k*0.13*SR); chirps[i:i+len(c)]+=c[:len(chirps)-i]
    return chirps
def amb_forest(D=48.0):
    tot=D+2.0; g=np.random.default_rng(101)
    L=np.zeros(int(tot*SR)); R=np.zeros_like(L)
    wl,gl=wind_bed(tot,111); wr,gr=wind_bed(tot,112)
    L+=wl*0.6; R+=wr*0.6
    leaves = hp(noise(tot,113),3000)*np.clip(lp(noise(tot,114),2,1)*40,0,1)**2*0.25
    L+=leaves*gl; R+=np.roll(leaves,4410)*gr
    t=0.8
    while t<tot-1.0:
        b=bird(g.uniform(2500,4200),0.6,int(g.integers(1e6)))*g.uniform(0.08,0.2)
        pan=g.uniform(0.15,0.85); i=int(t*SR)
        L[i:i+len(b)]+=b*(1-pan); R[i:i+len(b)]+=b*pan
        t+=g.uniform(1.5,5.0)
    st=np.stack([loopify(L),loopify(R)])
    return st
def babble(d, seed):
    g=np.random.default_rng(seed); t=t_(d)
    src=np.zeros(len(t)); ph=0
    f0=g.uniform(110,220); 
    pitch=f0*(1+0.12*lp(g.standard_normal(len(t)),3,1)*20)
    saw=signal.sawtooth(2*np.pi*np.cumsum(pitch)/SR)
    out=np.zeros(len(t)); B=2205
    vowels=[(700,1200),(400,2000),(300,2300),(500,900),(600,1700)]
    for i in range(0,len(t),B):
        f1,f2=vowels[g.integers(len(vowels))]
        seg=saw[i:i+B]
        out[i:i+B]=bp(seg,f1*0.8,f1*1.2,1)+0.6*bp(seg,f2*0.85,f2*1.15,1)
    syl=np.clip(np.sin(2*np.pi*g.uniform(3,5)*t+g.uniform(0,6)),0,1)
    phrase=(lp(g.standard_normal(len(t)),0.5,1)>0).astype(float); phrase=lp(phrase,8,1)
    return lp(out*syl*phrase,3000)
def amb_town(D=48.0):
    tot=D+2.0; g=np.random.default_rng(201)
    L=np.zeros(int(tot*SR)); R=np.zeros_like(L)
    for k in range(10):
        v=babble(tot,300+k)*g.uniform(0.3,0.7); pan=g.uniform(0.1,0.9)
        L+=v*(1-pan); R+=v*pan
    L=lp(L,2200); R=lp(R,2200)
    wl,_=wind_bed(tot,211); wr,_=wind_bed(tot,212)
    L=L*0.5+wl*0.25; R=R*0.5+wr*0.25
    scale=[1046,1175,1397,1568,1760,2093]; t=0.5
    while t<tot-2.5:
        n=g.integers(1,4)
        for j in range(n):
            f=scale[g.integers(len(scale))]; c=bell(f,2.2,(1,2.76,5.4),decay=1.6)*g.uniform(0.04,0.09)
            i=int((t+j*g.uniform(0.08,0.25))*SR); pan=g.uniform(0.3,0.7)
            L[i:i+len(c)]+=c[:len(L)-i]*(1-pan); R[i:i+len(c)]+=c[:len(R)-i]*pan
        t+=g.uniform(2.0,6.0)
    return np.stack([loopify(L),loopify(R)])
def write_loop(name, st, rms_db=-16):
    rms=np.sqrt(np.mean(st**2)); st=st/rms*10**(rms_db/20)
    p=np.max(np.abs(st)); st = st/p*0.89 if p>0.89 else st
    write(name, st, stereo=True, db=None, loop=True)

if __name__=='__main__':
    os.makedirs(OUT, exist_ok=True)
    sfx = {
        'step': s_step(1), 'step-dirt-02': s_step(2), 'step-dirt-03': s_step(3), 'step-dirt-04': s_step(4),
        'step-wood-01': s_step_wood(1), 'step-wood-02': s_step_wood(2),
        'move': s_move(), 'confirm': s_confirm(), 'cancel': s_cancel(), 'ring': s_ring(),
        'hit': s_hit(0), 'hit-heavy': s_hit(5, True), 'hit-crit': mix(s_hit(8,True), at(bell(1568,0.5,decay=6)*0.4,0.03,0.55)),
        'clean': s_clean(), 'miss': s_miss(), 'combo-finish': s_combo_finish(),
        'guard': s_guard(), 'heal': s_heal(), 'inkwing': s_inkwing(), 'seal': s_seal(),
        'coin': s_coin(), 'text': s_text(), 'wipe': s_wipe(),
        'enemy-hit': s_enemy_hit(), 'enemy-defeat': s_enemy_defeat(), 'lantern': s_lantern(), 'wind': s_wind(),
    }
    for k,v in sfx.items():
        db = -12 if k in ('wind','lantern') else (-6 if k in ('step','step-dirt-02','step-dirt-03','step-dirt-04','text','move') else -3)
        write(k, v, db=db); print('ok', k)
    write_loop('amb-forest', amb_forest()); print('ok amb-forest')
    write_loop('amb-town', amb_town(), -18); print('ok amb-town')
