"""Screenshots of the launcher page with made-up data (mock-htk.js), for UI previews.

    python3 build/ui-preview/shoot.py <output folder>
"""
import os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
UI = HERE.parent.parent / 'app' / 'ui' / 'index.html'
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / 'shots')
OUT.mkdir(parents=True, exist_ok=True)
MOCK = ((HERE / 'rom-preview-data.js').read_text(encoding='utf-8') if (HERE / 'rom-preview-data.js').exists() else '') + (HERE / 'mock-htk.js').read_text(encoding='utf-8')

SHOTS = [
    # name, query, phrase, actions
    ('01-splash', 'splash&page=upscale', 'Your Textures Look Like Ass. Fix Them.', ['splash']),
    ('01b-splash', 'splash&page=upscale', 'Expansion Pak for Your Eyeballs.', ['splash']),
    ('02-upscale', 'page=upscale', None, ['wait']),
    ('03-convert', 'page=convert', None, []),
    ('04-pack-recomp', 'page=pack&mode=pack', None, ['scroll']),
    ('05-pack-check', 'page=pack&mode=check', None, ['run']),
    ('06-ports-extract', 'page=ports&mode=extract', None, []),
    ('07-ports-build', 'page=ports&mode=build', None, []),
    ('08-legacy-import', 'page=legacy&mode=import', None, []),
    ('09-legacy-ship', 'page=legacy&mode=ship', None, []),
    ('10-settings-tools', 'page=settings&notools', None, []),
]

with sync_playwright() as p:
    exe = '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome'
    browser = p.chromium.launch(executable_path=exe if os.path.exists(exe) else None)
    for name, query, phrase, actions in SHOTS:
        ctx = browser.new_context(viewport={'width': 1280, 'height': 800}, device_scale_factor=1, bypass_csp=True)
        init = MOCK + (f"\nwindow.__phrase = {{ text: {phrase!r} }};" if phrase else '')
        ctx.add_init_script(init)
        page = ctx.new_page()
        page.goto(UI.as_uri() + '?' + query)
        page.wait_for_timeout(400)
        if 'splash' in actions:
            page.wait_for_timeout(700)
            page.evaluate('document.getAnimations().forEach(a => a.pause())')
        if 'wait' in actions:
            page.wait_for_timeout(600)
        if 'run' in actions:
            page.click('#go'); page.wait_for_timeout(300)
        if 'scroll' in actions:
            page.evaluate("document.querySelector('#page').scrollTop = 420"); page.wait_for_timeout(150)
        page.screenshot(path=str(OUT / f'{name}.png'))
        ctx.close()
    browser.close()
print('saved to', OUT)
