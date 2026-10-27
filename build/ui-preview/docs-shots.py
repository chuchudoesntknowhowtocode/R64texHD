"""Screenshots for the README (docs/screenshots), made from the real interface with sample data.

    node build/ui-preview/make-preview-data.js && python3 build/ui-preview/docs-shots.py
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
UI = ROOT / 'app' / 'ui' / 'index.html'
OUT = ROOT / 'docs' / 'screenshots'
OUT.mkdir(parents=True, exist_ok=True)
MOCK = (HERE / 'mock-htk.js').read_text(encoding='utf-8')
DATA = (HERE / 'preview-data.js').read_text(encoding='utf-8') if (HERE / 'preview-data.js').exists() else ''

# name, query, actions, header phrase
SHOTS = [
    ('welcome', 'setup', [], 'HD Texture Packs for Games That Refuse to Die.'),
    ('upscale', 'page=upscale', ['wait'], 'Making Muddy Textures Eat Their Vegetables.'),
    ('convert-rt64-dump', 'page=convert', ['scroll:250'], 'Expansion Pak for Your Eyeballs.'),
    ('pack-recomp-info', 'page=pack&mode=pack', ['scroll:430'], 'More Pixels Than Nintendo Ever Intended.'),
    ('check-a-pack', 'page=pack&mode=check', ['run'], 'Rendering Nostalgia. Destroying Blur.'),
    ('ship-mods-o2r', 'page=ports&mode=build', ['scroll:120'], 'Because Even Mario Deserves Better Skin.'),
    ('rice-gliden64', 'page=legacy&mode=import', [], 'Built Different. Runs on Nostalgia.'),
    ('settings', 'page=settings&notools', ['scroll:300'], 'Same Game. Less Fugly.'),
    ('settings-look-and-feel', 'page=settings', ['click:[data-key="splash"] [data-v="true"]', 'scroll:99999'], 'Rendering Nostalgia. Destroying Blur.'),
]

with sync_playwright() as p:
    exe = '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome'
    browser = p.chromium.launch(executable_path=exe if os.path.exists(exe) else None)
    for name, query, actions, phrase in SHOTS:
        ctx = browser.new_context(viewport={'width': 1280, 'height': 800}, device_scale_factor=1, bypass_csp=True)
        init = DATA + MOCK + "\nwindow.__phrase = { text: 'Your Textures Look Like Ass. Fix Them.' };"
        if phrase: init += f"\nwindow.__hdrStart = {phrase!r};"
        ctx.add_init_script(init)
        page = ctx.new_page()
        page.goto(UI.as_uri() + '?' + query)
        page.wait_for_timeout(500)
        for a in actions:
            if a == 'splash':
                page.wait_for_timeout(1300); page.evaluate('document.getAnimations().forEach(a => a.pause())')
            elif a == 'wait':
                page.wait_for_timeout(700)
            elif a == 'run':
                page.click('#go'); page.wait_for_timeout(400)
            elif a.startswith('click:'):
                page.click(a[6:]); page.wait_for_timeout(200)
            elif a.startswith('scroll:'):
                page.evaluate(f"document.querySelector('#page').scrollTop = {a.split(':')[1]}"); page.wait_for_timeout(200)
        page.screenshot(path=str(OUT / f'{name}.png'))
        ctx.close()
    browser.close()
print('saved to', OUT)
