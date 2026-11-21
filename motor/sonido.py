"""Música y efectos generados con numpy (nada copiado). Lee los tiempos de index.html (CONFIG).

Uso: python3 sonido.py sonido.wav
- Base: 100 pulsos por minuto, bombo, palmas, platillo corto, bajo y acordes suaves (La menor, Fa, Do, Sol).
- Efectos: whoosh en cada cambio de escena, pop en cada texto que aparece, ding en cada mensaje,
  golpe en cada sello, subida antes de la revelación y un final brillante.
"""
import json, os, re, sys, wave
import numpy as np
from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
SR = 44100
rng = np.random.default_rng(7)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    pg = b.new_page()
    pg.goto('file://' + os.path.join(AQUI, 'index.html'))
    C = pg.evaluate('JSON.parse(JSON.stringify(CONFIG))')
    b.close()

T = C['duracion']
N = int(T * SR)
mus = np.zeros(N)
sfx = np.zeros(N)
tt = np.arange(N) / SR


def put(buf, t0, sig, vol=1.0):
    i = int(t0 * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    buf[i:j] += sig[:j - i] * vol


def env(n, a=0.005, d=0.2):
    x = np.arange(n) / SR
    return np.minimum(1, x / a) * np.exp(-x / d)


def lowpass(x, k):
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += k * (x[i] - acc)
        y[i] = acc
    return y


# ---------- música ----------
bpm = 100
beat = 60 / bpm
chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)]
bass = [110.0, 87.31, 130.81, 98.0]
nb = int(T / beat) + 1
for k in range(nb):
    t0 = k * beat
    # bombo
    n = int(0.3 * SR); x = np.arange(n) / SR
    f = 45 + 90 * np.exp(-x * 30)
    put(mus, t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 9), 0.9)
    # palmas en 2 y 4
    if k % 2 == 1:
        n = int(0.18 * SR)
        put(mus, t0, rng.standard_normal(n) * env(n, 0.002, 0.05), 0.25)
    # platillo en corcheas
    for h in (0, 0.5):
        n = int(0.05 * SR)
        hh = rng.standard_normal(n)
        hh = hh - lowpass(hh, 0.5)
        put(mus, t0 + h * beat, hh * env(n, 0.001, 0.015), 0.18)
    # bajo
    bar = (k // 4) % 4
    n = int(beat * 0.9 * SR); x = np.arange(n) / SR
    put(mus, t0, (np.sin(2 * np.pi * bass[bar] * x) + 0.3 * np.sin(4 * np.pi * bass[bar] * x)) * env(n, 0.01, 0.35), 0.35)
# acordes por compás
for bi in range(int(T / (4 * beat)) + 1):
    t0 = bi * 4 * beat
    n = int(4 * beat * SR); x = np.arange(n) / SR
    ch = chords[bi % 4]
    pad = sum(np.sin(2 * np.pi * f * x) + 0.5 * np.sin(2 * np.pi * f * 1.003 * x) for f in ch)
    e = np.minimum(1, x / 0.4) * np.minimum(1, (4 * beat - x) / 0.4)
    put(mus, t0, pad * e, 0.06)
    # arpegio
    for s in range(8):
        f = ch[s % 3] * 2
        m = int(0.25 * SR); y = np.arange(m) / SR
        put(mus, t0 + s * beat / 2, np.sin(2 * np.pi * f * y) * env(m, 0.003, 0.12), 0.07)

# entrada y salida de la música
mus *= np.clip(tt / 0.3, 0, 1) * np.clip((T - tt) / 1.2, 0, 1)

# ---------- efectos ----------
def whoosh(t0, dur=0.45, vol=0.35):
    n = int(dur * SR); x = np.arange(n) / SR
    w = rng.standard_normal(n)
    k = 0.02 + 0.5 * np.sin(np.pi * x / dur) ** 2
    y = np.zeros(n); acc = 0.0
    for i in range(n):
        acc += k[i] * (w[i] - acc); y[i] = acc
    put(sfx, t0 - dur * 0.6, y * np.sin(np.pi * x / dur) ** 2, vol * 2.2)


def popfx(t0, vol=0.22):
    n = int(0.07 * SR); x = np.arange(n) / SR
    f = 500 + 1400 * x / 0.07
    put(sfx, t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.03), vol)


def ding(t0, vol=0.3):
    n = int(0.6 * SR); x = np.arange(n) / SR
    put(sfx, t0, (np.sin(2 * np.pi * 1318.5 * x) + 0.5 * np.sin(2 * np.pi * 1975.5 * x)) * env(n, 0.002, 0.18), vol)


def golpe(t0, vol=0.7):
    n = int(0.35 * SR); x = np.arange(n) / SR
    f = 50 + 120 * np.exp(-x * 25)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 10) + 0.4 * rng.standard_normal(n) * np.exp(-x * 40)
    put(sfx, t0, s, vol)


def subida(t0, dur=1.0, vol=0.25):
    n = int(dur * SR); x = np.arange(n) / SR
    f = 200 + 1600 * (x / dur) ** 2
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 + lowpass(rng.standard_normal(n), 0.15) * 1.5
    put(sfx, t0 - dur, s * (x / dur) ** 2, vol)


esc = C['escenas']
for i, s in enumerate(esc):
    a = s['t'][0]
    if i > 0:
        whoosh(a)
    if s.get('robot'):
        popfx(a + 0.35, 0.25)
    if s['tipo'] == 'gancho':
        golpe(a + 0.08, 0.5); popfx(a + 0.05)
    if s['tipo'] == 'chat':
        for k in range(len(s['mensajes'])):
            ding(a + 1.0 + k * 1.0)
        golpe(a + 2.6, 0.45)
    if s['tipo'] == 'revelacion':
        subida(a, 1.0); golpe(a + 0.05, 0.8)
    if s['tipo'] == 'consecuencia':
        for k in range(len(s['chats'])):
            popfx(a + 0.6 + k * 1.0); golpe(a + 1.0 + k * 1.0, 0.55)
    if s['tipo'] == 'pasos':
        for k in range(len(s['pasos'])):
            whoosh(a + 0.55 + k * 2.1, 0.3, 0.2); ding(a + 0.7 + k * 2.1, 0.18)
    if s['tipo'] == 'cierre':
        golpe(a + 0.05, 0.4)
        for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
            n = int(0.5 * SR); x = np.arange(n) / SR
            put(sfx, a + 0.5 + k * 0.08, np.sin(2 * np.pi * f * x) * env(n, 0.003, 0.25), 0.15)
# pops suaves de subtítulos (una por cada palabra clave)
for c in C['subtitulos']:
    words = c[2].split(' ')
    n = len(words); span = min(c[1] - c[0], n * 0.28 + 0.3)
    for k, w in enumerate(words):
        if w.startswith('*') or w.startswith('_'):
            popfx(c[0] + k * (span - 0.3) / max(1, n), 0.12)

# mezcla: la música baja cuando hay efectos fuertes
lvl = lowpass(np.abs(sfx), 0.001)
duck = 1 - 0.5 * np.clip(lvl / (lvl.max() + 1e-9) * 3, 0, 1)
mix = mus * 0.55 * duck + sfx
mix = np.tanh(mix * 1.2)
mix = mix / np.max(np.abs(mix)) * 0.89
st = np.stack([mix, mix], 1)
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
print('ok', T, 's')
