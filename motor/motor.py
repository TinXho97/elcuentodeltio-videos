"""Filma index.html (motor de video SID) escena por escena.

Uso:
  python3 motor.py prueba 1.2 5.5 9 14 21 27     -> cuadros de prueba prueba_XX.jpg
  python3 motor.py escenas 0 2 4                 -> filma esas escenas en escenas/eNN.mp4 (correr 2 procesos en paralelo)
  python3 motor.py unir salida.mp4 sonido.wav    -> une las escenas y agrega el sonido
Necesita Chrome, Playwright y ffmpeg. 1080x1920, 30 cuadros por segundo.
"""
import json, os, subprocess, sys
from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
FPS = 30
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(FPS)]


def pagina(p):
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 1080, 'height': 1920})
    pg.goto('file://' + os.path.join(AQUI, 'index.html'))
    pg.wait_for_timeout(800)
    return b, pg


def main():
    modo = sys.argv[1]
    if modo == 'unir':
        salida, sonido = sys.argv[2], sys.argv[3]
        es = sorted(f for f in os.listdir(os.path.join(AQUI, 'escenas')) if f.endswith('.mp4') and not f.startswith('tmp'))
        lista = os.path.join(AQUI, 'escenas', 'lista.txt')
        open(lista, 'w').write(''.join(f"file '{f}'\n" for f in es))
        mudo = os.path.join(AQUI, 'escenas', 'tmp_mudo.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lista, '-c', 'copy', mudo], check=True)
        tmp = salida[:-4] + '.tmp.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mudo, '-i', sonido, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', tmp], check=True)
        os.replace(tmp, salida)
        return
    with sync_playwright() as p:
        b, pg = pagina(p)
        if modo == 'prueba':
            for t in [float(x) for x in sys.argv[2:]]:
                pg.evaluate(f'render({t})')
                pg.screenshot(path=os.path.join(AQUI, f'prueba_{t:05.2f}.jpg'), type='jpeg', quality=88)
        elif modo == 'escenas':
            esc = pg.evaluate('CONFIG.escenas.map(s=>s.t)')
            os.makedirs(os.path.join(AQUI, 'escenas'), exist_ok=True)
            for i in [int(x) for x in sys.argv[2:]]:
                a, z = esc[i]
                f0, f1 = round(a * FPS), round(z * FPS)
                tmp = os.path.join(AQUI, 'escenas', f'tmp_e{i:02d}.mp4')
                ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'mjpeg',
                                       '-i', '-', *ENC, tmp], stdin=subprocess.PIPE)
                for f in range(f0, f1):
                    pg.evaluate(f'render({f / FPS})')
                    ff.stdin.write(pg.screenshot(type='jpeg', quality=92))
                ff.stdin.close()
                if ff.wait() == 0:
                    os.replace(tmp, os.path.join(AQUI, 'escenas', f'e{i:02d}.mp4'))
                else:
                    raise SystemExit(f'falló la escena {i}')
        b.close()


if __name__ == '__main__':
    main()
