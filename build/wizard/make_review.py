"""Renders every video for the Wizard Scene Review page (v2) and a manifest.json describing them.
    python3 make_review.py <out dir> [group ...]      groups: runs fights clips peeks trips extra tests busy"""
import os, sys, json, glob
import numpy as np
import review_build as RB
import fights, elf_fight, clips, s11
import scenes2, scenes3, scenes4, elf2

HERE = os.path.dirname(os.path.abspath(__file__))
APPROVED = os.path.join(HERE, 'assets', 'approved')            # the 11 scenes the owner approved (GIFs)
TESTS = os.path.join(HERE, 'assets', 'tests')                  # older fighter tests (GIFs, kept as they are)
OUT = sys.argv[1]; GROUPS = sys.argv[2:] or ['runs', 'fights', 'clips', 'peeks', 'trips', 'extra', 'tests', 'busy']
VID = os.path.join(OUT, 'videos'); os.makedirs(VID, exist_ok=True)
MAN = os.path.join(OUT, os.environ.get('MANIFEST', 'manifest.json'))
manifest = json.load(open(MAN)) if os.path.exists(MAN) else {}

def save(key, run, title, group, note='', marks=None):
    mp4 = os.path.join(VID, key + '.mp4'); poster = os.path.join(VID, key + '.png')
    n = run.n; run.encode(mp4, poster)
    manifest[key] = dict(title=title, group=group, note=note, frames=n, seconds=round(n / 30, 1), marks=marks or run.marks,
                         video=f'videos/{key}.mp4', poster=f'videos/{key}.png')
    json.dump(manifest, open(MAN, 'w'), indent=1); print(key, n, flush=True)

def linear(total): return lambda n: min(1.0, n / max(1, total))
def fight_fn(name, **kw): return lambda: fights.render(name, **kw)
LEN = {}
def length(key, fn):
    if key not in LEN: LEN[key] = len(fn())
    return LEN[key]

# ------------------------------------------------------------------ chained runs
def chain(key, title, parts, note):
    """parts: list of (label, kind, src); kind 'scene' (callable) | 'gif' (path) | 'peek' (between-scene wait: gap, peek 11, gap)"""
    peek_n = length('s11', s11.s11)
    lens = []
    for label, kind, src in parts:
        lens.append(length(label, src) if kind == 'scene' else RB.gif_len(src) if kind == 'gif' else peek_n)
    body = sum(lens)
    gap = RB.gap_len(1 / (body + 120 * sum(1 for p in parts if p[1] == 'peek')))
    total = body + 2 * gap * sum(1 for p in parts if p[1] == 'peek')
    prog = linear(total)
    run = RB.Run(os.path.join(OUT, 'tmp_' + key))
    for (label, kind, src) in parts:
        if kind == 'scene': run.add(RB.from_scene(src), prog, label=label)
        elif kind == 'gif': run.add(RB.from_gif(src), prog, label=label)
        else:
            run.gap(gap, prog, label='wait'); run.add(RB.from_scene(s11.s11), prog, label='peek'); run.gap(gap, prog)
    run.gap(40, lambda n: 1.0, label='job done', state=lambda i: 'run' if i < 10 else 'idle')
    save(key, run, title, 'Chained runs', note)

def ending(kind):
    at = 200
    fn = fight_fn('goblin', robed=True, end=(kind, at)); n_all = length(f'end_{kind}', fn); n_job = n_all - (fights.EXIT_N if kind == 'exit' else fights.BURST_N)
    run = RB.Run(os.path.join(OUT, 'tmp_end_' + kind))
    if kind == 'exit':
        prog = linear(n_job); run.add(RB.from_scene(fn), prog, label='job finishes at the 23-hit mark')
        run.gap(30, lambda n: 1.0, state=lambda i: 'run' if i < 10 else 'idle')
        save('end_success', run, 'Job finishes mid-fight: instant exit', 'Chained runs', 'The job hits 100% in the middle of the combo: the goblin is knocked into the pipe and he follows, in under a second.')
    else:
        rate = 1 / (n_job * 1.7); pc = n_job * rate
        def prog(n): return n * rate if n < n_job else pc * max(0.0, 1 - (n - n_job - 16) / 24)
        state = lambda i: 'run' if i < n_job else ('fail', i - n_job)
        run.add(RB.from_scene(fn), prog, state=state, label=f'job {"cancelled" if kind == "cancel" else "fails"}')
        run.gap(40, lambda n: pc * max(0.0, 1 - (n - n_job - 16) / 24), state=lambda i: ('fail', fights.BURST_N + i) if i < 30 else 'idle')
        save('end_' + kind, run, f'Job {"cancelled" if kind == "cancel" else "fails"} mid-fight: {"yellow" if kind == "cancel" else "red"} burst', 'Chained runs',
             'The burst rule is unchanged: two rings of 8 pixel circles, the outer one faster and blinking, gone after 1 s. The bar flashes red twice and drains.')

def runs():
    chain('run_robe', 'Robe carry-over', [
        ('goblin (robed, robe and hat burn)', 'scene', fight_fn('goblin', robed=True)), ('between', 'peek', None),
        ('robot (still in the gi, rocket punch lands)', 'scene', fight_fn('robot', robed=False, odd_hit=True)), ('between', 'peek', None),
        ('re-robe (pixel rebuild)', 'scene', clips.rerobe), ('classic 07 bubble float', 'gif', os.path.join(APPROVED, '07_bubble_float.gif'))],
        'One job: the robe and hat burn in the first fight, he stays in the gi for the next one, and the robe rebuilds before a classic scene. Between scenes: wait, the peek, wait.')
    chain('run_twin', 'Dark twin comeback', [('dark twin (wins round 1, wizard comes back)', 'scene', fight_fn('twin', robed=True, twin_wins_r1=True))],
          'MIRROR MATCH, red eyes. The twin takes round 1 (about 1 in 3 fights), floors him, taunts; ROUND 2 and the wizard wins.')
    chain('run_bonus', 'Bonus car after 3 wins', [
        ('win 1: goblin (robed)', 'scene', fight_fn('goblin', robed=True)), ('between', 'peek', None),
        ('win 2: golem (gi, shockwave lands)', 'scene', fight_fn('golem', robed=False, odd_hit=True)), ('between', 'peek', None),
        ('win 3: dark twin (gi)', 'scene', fight_fn('twin', robed=False)), ('between', 'peek', None),
        ('BONUS STAGE: car (gi)', 'scene', fight_fn('car', robed=False))],
        'Three wins in a row earn the bonus car next. The win count is saved between launches.')
    for k in ('exit', 'cancel', 'error'): ending(k)

# ------------------------------------------------------------------ single clips
def single(key, title, group, fn_or_gif, note='', state='run', gif=False):
    n = RB.gif_len(fn_or_gif) if gif else length(key, fn_or_gif)
    run = RB.Run(os.path.join(OUT, 'tmp_' + key))
    run.add(RB.from_gif(fn_or_gif) if gif else RB.from_scene(fn_or_gif), (lambda m: 0.0) if state == 'idle' else linear(n), state=state)
    save(key, run, title, group, note)

def fights_group():
    for key, title, kw, note in [
        ('fight_goblin', 'Goblin, robed start', dict(robed=True), 'VS card, rock bonk, the hat flies off burning with the robe, combo, smash, K.O.'),
        ('fight_goblin_gi', 'Goblin, already in the gi', dict(robed=False), 'Same fight later in a job: no burn, the rock hits him, power-up instead.'),
        ('fight_golem', 'Golem, gi, shockwave lands', dict(robed=False, odd_hit=True), 'The odd hit: the ground-pound shockwave knocks him back; he shakes it off.'),
        ('fight_robot', 'Robot, robed, rocket punch lands', dict(robed=True, odd_hit=True), 'The rocket punch connects instead of being parried.'),
        ('fight_twin', 'Dark twin, robed (no round-1 loss)', dict(robed=True), 'MIRROR MATCH, red eyes, both robes and hats burn.'),
        ('fight_car', 'Bonus car, in the gi', dict(robed=False), 'BONUS STAGE after 3 wins.')]:
        name = key.split('_')[1]
        single(key, title, 'Fights', fight_fn(name, **kw), note)
    single('fight_elf', 'Machine elf (Psychedelic on)', 'Fights', fight_fn('elf', robed=True),
           'Hexagram shield he smashes through, reality-warp portals, clone swarm; K.O. as a rainbow helix into the pipe. Light-touch arena.')

def clips_group():
    single('rerobe', 'Re-robe: pixel rebuild', 'Clips', clips.rerobe, 'Before a classic or trip scene (or the next job) when the robe burned off.')
def peeks():
    run = RB.Run(os.path.join(OUT, 'tmp_peeks'))
    for p in clips.PHRASES:
        run.add(RB.from_scene(lambda p=p: clips.idle_peek(p)), lambda n: 0.0, state='idle', label=p)
        run.gap(20, lambda n: 0.0, state='idle')
    save('idle_peeks', run, 'Idle peeks: all 11 phrases', 'Clips', 'No job running: every 20 s (60 s after 5 min idle). Shuffled, no repeats until all 11 have shown. Shown back to back here.')
def busy():
    single('busy_11', 'Busy peek (scene 11), new style', 'Clips', s11.s11, 'No percentage yet / quick jobs / between scenes. Re-rendered with the new head.', state='idle')
def trips():
    for mod in (scenes3, scenes4):
        for i, (name, fn) in mod.SCENES.items():
            single('trip_' + name, name.split('_', 1)[1].replace('_', ' ').capitalize(), 'Psychedelic: LSD' if mod is scenes3 else 'Psychedelic: DMT', fn, 'Re-rendered in the new style.')
    single('trip_43_dmt_machine_elf_sacred_warp', 'Machine elf sacred warp (43)', 'Psychedelic: DMT', elf2.scene, 'The approved elf scene, re-rendered with the new wizard where he appears.')
def extra():
    for i, (name, fn) in scenes2.SCENES.items():
        single('extra_' + name, name.split('_', 1)[1].replace('_', ' ').capitalize(), 'Found in the toolkit (12-21)', fn, 'Not in the pool: you said there are no scenes 12-21, but the toolkit has these. In or out?')
def tests():
    for g in sorted(glob.glob(os.path.join(TESTS, '*.gif'))):
        key = 'test_' + os.path.basename(g)[:-4].replace('sf_red_gi_example', 'red_gi').replace('sf_example', 'robe_staff')
        single(key, os.path.basename(g)[:-4].replace('sf_red_gi_example', 'red gi').replace('sf_example', 'robe + staff').replace('_', ' '), 'Older fighter tests', g, 'Kept as they are (old style).', gif=True)

FN = dict(runs=runs, fights=fights_group, clips=clips_group, peeks=peeks, trips=trips, extra=extra, tests=tests, busy=busy)
for g in GROUPS: FN[g]()
