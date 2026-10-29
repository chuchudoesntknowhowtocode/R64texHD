"""Screenshots for the README (docs/screenshots), made from the real interface with sample data, plus a small
thumbnail of each (docs/screenshots/thumbs) and an animated preview of the wizard footer.

    node build/ui-preview/make-preview-data.js && python3 build/ui-preview/docs-shots.py [name ...]
"""
import functools, http.server, os, sys, threading
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / 'docs' / 'screenshots'
THUMBS = OUT / 'thumbs'
OUT.mkdir(parents=True, exist_ok=True); THUMBS.mkdir(exist_ok=True)
MOCK = (HERE / 'mock-htk.js').read_text(encoding='utf-8')
DATA = ''.join((HERE / n).read_text(encoding='utf-8') for n in ('preview-data.js', 'rom-preview-data.js') if (HERE / n).exists())
THUMB_W = 400

# The page is served over http so the footer scenes and sounds load like in the app.
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'app')))
srv.RequestHandlerClass.log_message = lambda *a, **k: None
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{srv.server_address[1]}/ui/index.html'

QUIET = "Wizard._debug().D.nextPeekAt = performance.now() + 1e9; Wizard._stop()"
# name, query, actions, header phrase
SHOTS = [
    ('welcome', 'page=welcome', [], 'HD Texture Packs for Games That Refuse to Die.'),
    ('first-launch-psychedelic', 'setup', ['sleep:3700'], 'HD Texture Packs for Games That Refuse to Die.'),
    ('first-launch-tools', 'setup&notools', ['sleep:3700'], 'HD Texture Packs for Games That Refuse to Die.'),
    ('upscale', 'page=upscale', ['wait', 'js:document.querySelector("#preview").style.position="static"', 'scroll:330', 'wait'], 'Making Muddy Textures Eat Their Vegetables.'),
    ('upscale-compare', 'page=upscale', ['wait', 'js:setSplit(.42)'], 'Making Muddy Textures Eat Their Vegetables.'),
    ('convert-rt64-dump', 'page=convert', ['scroll:250'], 'Expansion Pak for Your Eyeballs.'),
    ('pack-recomp-info', 'page=pack&mode=pack', ['scroll:430'], 'More Pixels Than Nintendo Ever Intended.'),
    ('check-a-pack', 'page=pack&mode=check', ['run'], 'Rendering Nostalgia. Destroying Blur.'),
    ('ship-mods-o2r', 'page=ports&mode=extract&ship=ghost', ['wait'], 'Because Even Mario Deserves Better Skin.'),
    ('ship-mods-ports', 'page=ports&mode=extract&ship=ghost', ['wait', 'scroll:99999'], 'Because Even Mario Deserves Better Skin.'),
    ('rice-gliden64', 'page=legacy&mode=import', [], 'Built Different. Runs on Nostalgia.'),
    ('rom-tools', 'page=roms', ['click:.rom-item:has-text("GOLDENEYE")', 'wait'], 'Your Childhood Called. Its Graphics Are Embarrassing.'),
    ('settings', 'page=settings&notools', ['sleep:3700', 'js:closeModal()', 'wait'], 'Same Game. Less Fugly.'),
    ('settings-wizard', 'page=settings', ['wait', 'js:document.querySelector("#page").scrollTop = document.querySelector("#page .sbox:nth-of-type(4)").offsetTop + 200'], 'Rendering Nostalgia. Destroying Blur.'),
    ('settings-sound', 'page=settings', ['wait', 'js:document.querySelector("#page").scrollTop = document.querySelector("#page .sbox:nth-of-type(5)").offsetTop - 16'], 'Rendering Nostalgia. Destroying Blur.'),
    ('menu-folded', 'page=upscale', ['wait', 'click:#nav-fold', 'sleep:400'], 'Same Game. Less Fugly.'),
]
FOOTER = 'wizard-footer'           # animated: a fight in the footer while a job runs


def thumb(name):
    im = Image.open(OUT / f'{name}.png').convert('RGB')
    im = im.resize((THUMB_W, round(im.height * THUMB_W / im.width)), Image.LANCZOS)
    im.save(THUMBS / f'{name}.jpg', quality=84, optimize=True, progressive=True)


def footer_anim(page):
    """a goblin fight in the footer with the bar part-filled: animated WebP + a still and a thumbnail"""
    import io, time
    page.evaluate(QUIET)
    page.evaluate("(() => { const b = Wizard._debug().bar; b.mode = 'run'; b.p = 0.2; window.__t = setInterval(() => { b.p = Math.min(0.9, b.p + 0.002); }, 100); })()")
    page.evaluate("(() => { const d = Wizard._debug(); d.D.peeking = true; d.D.busyN = 0; Wizard._stop(); Wizard._play('fight_goblin_robed'); })()")
    for _ in range(60):
        if page.evaluate("(Wizard._debug().cur || {}).id === 'fight_goblin_robed'"): break
        page.wait_for_timeout(100)
    frames, t0 = [], time.time()
    clip = {'x': 0, 'y': 700, 'width': 1280, 'height': 100}
    while page.evaluate("!!Wizard._debug().cur") and len(frames) < 400:
        frames.append(Image.open(io.BytesIO(page.screenshot(clip=clip))).convert('RGB'))
        if len(frames) == 120:                                            # the whole window mid-fight, for the feature grid
            page.screenshot(path=str(OUT / 'wizard-app.png')); thumb('wizard-app')
    ms = max(40, round((time.time() - t0) * 1000 / max(1, len(frames))))
    frames[0].save(OUT / f'{FOOTER}.webp', save_all=True, append_images=frames[1:], duration=ms, loop=0, quality=80, method=4)
    big = frames[len(frames) * 3 // 5]; big.save(OUT / f'{FOOTER}.png')
    big.resize((THUMB_W * 2, round(big.height * THUMB_W * 2 / big.width)), Image.LANCZOS).save(THUMBS / f'{FOOTER}.jpg', quality=86)
    print('footer frames', len(frames), ms, 'ms')


only = set(sys.argv[1:])
with sync_playwright() as p:
    exe = '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome'
    browser = p.chromium.launch(executable_path=exe if os.path.exists(exe) else None)
    def open_page(query, phrase):
        ctx = browser.new_context(viewport={'width': 1280, 'height': 800}, device_scale_factor=1, bypass_csp=True)
        init = DATA + MOCK + "\nwindow.__phrase = { text: 'Your Textures Look Like Ass. Fix Them.' };"
        if phrase: init += f"\nwindow.__hdrStart = {phrase!r};"
        ctx.add_init_script(init)
        page = ctx.new_page(); page.goto(BASE + '?' + query); page.wait_for_timeout(900)
        page.evaluate(QUIET); page.wait_for_timeout(300); page.evaluate(QUIET)    # a stopped peek starts one more phrase: stop that too
        return ctx, page
    for name, query, actions, phrase in SHOTS:
        if only and name not in only: continue
        ctx, page = open_page(query, phrase)
        for a in actions:
            if a.startswith('sleep:'): page.wait_for_timeout(int(a[6:]))
            elif a == 'wait': page.wait_for_timeout(700)
            elif a == 'run': page.click('#go'); page.wait_for_timeout(400)
            elif a.startswith('click:'): page.click(a[6:]); page.wait_for_timeout(200)
            elif a.startswith('js:'): page.evaluate(a[3:]); page.wait_for_timeout(250)
            elif a.startswith('scroll:'): page.evaluate(f"document.querySelector('#page').scrollTop = {a.split(':')[1]}"); page.wait_for_timeout(200)
        page.screenshot(path=str(OUT / f'{name}.png'))
        thumb(name)
        ctx.close()
    if not only or FOOTER in only:
        ctx, page = open_page('page=upscale', 'Same Game. Less Fugly.')
        footer_anim(page); ctx.close()
    browser.close()
srv.shutdown()
print('saved to', OUT)
