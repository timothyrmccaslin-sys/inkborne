#!/usr/bin/env python3
"""Copy reviewed team deliverables into the live data/ and assets/ folders (Marc, integrator).
Re-run whenever a team drop changes. Anything the teams haven't delivered stays as an
integrator placeholder in data/ (marked with "_todo")."""
import json, shutil, os, glob, re
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = lambda *p: os.path.join(R, 'team', *p)
D = lambda *p: os.path.join(R, 'data', *p)
def load(p): return json.load(open(p, encoding='utf-8'))
def save(p, o): json.dump(o, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
def fix(s): return s.replace('Tabula Rasa', 'Inkborne').replace('Spirit Ink', 'Vermilion Ink')

# party: Jake (systems). The demo party starts at level 5; Itsuki starts with 85 ink so Unfurl shows in the first fight.
p = load(T('systems', 'jake', 'party.json'))
DEMO_LV, START_INK = 5, {'itsuki': 85, 'benika': 30, 'gonzo': 20}
for m in p['members']:
    row = m['stat_table'][DEMO_LV - 1]
    for k in ('hp', 'atk', 'def', 'mat', 'mdf', 'spd'): m[k] = row[k]
    m['lv'] = DEMO_LV; m['ink'] = START_INK.get(m['id'], 0)
    m['strokes'] = [s for s in m['strokes'] if s.get('unlock_lv', 1) <= DEMO_LV]
    if m['seal']['name'] == 'Crane Gale Script': m['seal']['name'] = 'Gale Crane Script'  # Lisa's approved rename
    for k in ('stat_table',): m.pop(k, None)
p.pop('progression', None)
save(D('party.json'), p)
shutil.copy(T('systems', 'jake', 'transformation.json'), D('transformation.json'))
shutil.copy(T('systems', 'jake', 'elements.json'), D('elements.json'))

# items + shop: Ollie's ids/names (story) with Jane's numbers mapped by Kekai
shutil.copy(T('story', 'items.json'), D('items.json'))
shutil.copy(T('story', 'shops.json'), D('shops.json'))

# strings (Jamie), barks (Ollie), dialogue (Ollie), story (Lisa)
st = {k: fix(v) for k, v in load(T('story', 'strings.json')).items()}
st['battle.gauge.label'] = 'Vermilion Ink'
st.setdefault('game.title', 'Inkborne')
save(D('strings.json'), st)
save(D('barks.json'), load(T('story', 'barks.json')))
dl = load(T('story', 'dialogue.json'))
# TODO(story): SPEC asks for dialogue choices; Ollie's scene has none yet, so the integrator adds one branch at n12.
n = dl['hanshi_dusk']['nodes']
if 'n12' in n and not n['n12'].get('choices'):
    n['n11']['choices'] = [
        {'text': 'I need somewhere to sleep. Hard to sleep with ink-beasts at the door.', 'next': 'n12'},
        {'text': "Point me at whatever's breaking the seals.", 'next': 'n12b', 'set': 'eager'}]
    n['n11'].pop('next', None)
    n['n12b'] = {'who': 'itsuki', 'mood': 'calm', 'text': "Point me at whatever's breaking the seals. I'd like a word with it.", 'next': 'n13', '_todo': 'integrator line, pending Ollie'}
save(D('dialogue.json'), dl)
sj = load(T('story', 'story.json')); sj['title'] = 'Inkborne'
save(D('story.json'), sj)

# enemies: TODO(systems/Karen) stats not delivered yet -> integrator placeholders; names (Lisa), mon (Jane)
mon = load(T('systems', 'jane', 'data', 'enemies.mon.json'))['mon']
save(D('enemies.json'), {'_todo': 'enemy stats are integrator placeholders until Karen delivers', 'enemies': [
  {'id': 'blotling', 'name': 'Blotling', 'element': 'dusk', 'hp': 110, 'atk': 22, 'def': 6, 'mat': 16, 'mdf': 4, 'spd': 12, 'mon': mon['blotling'],
   'moves': [{'id': 'splash', 'name': 'Ink Splash', 'kind': 'phys', 'power': 1.0, 'weight': 3}, {'id': 'seep', 'name': 'Seep', 'kind': 'elem', 'power': 1.1, 'element': 'dusk', 'weight': 1}]},
  {'id': 'hollow_lantern', 'name': 'Hollow Lantern', 'element': 'gale', 'hp': 150, 'atk': 18, 'def': 8, 'mat': 24, 'mdf': 10, 'spd': 15, 'mon': mon['hollow_lantern'],
   'moves': [{'id': 'dim', 'name': 'Dimming Curse', 'kind': 'elem', 'power': 1.15, 'element': 'gale', 'weight': 2}, {'id': 'singe', 'name': 'Grey Singe', 'kind': 'phys', 'power': 0.9, 'weight': 1}]},
  {'id': 'smudge_ronin', 'name': 'Smudge Ronin', 'element': 'stone', 'hp': 620, 'atk': 30, 'def': 16, 'mat': 22, 'mdf': 14, 'spd': 13, 'mon': mon['smudge_ronin'],
   'moves': [{'id': 'drip', 'name': 'Dripping Cut', 'kind': 'phys', 'power': 1.1, 'weight': 3}, {'id': 'unwrite', 'name': 'Unwriting Slash', 'kind': 'elem', 'power': 1.3, 'element': 'stone', 'weight': 1}]}],
  'encounters': {'sumikage_c': ['blotling', 'hollow_lantern', 'blotling'], 'sumikage_boss': ['smudge_ronin']}})

# audio: James (sfx), Rita (voice)
for f in glob.glob(T('audio', 'sfx', '*.mp3')): shutil.copy(f, os.path.join(R, 'assets', 'sfx'))
for f in glob.glob(T('audio', 'voice', '*.mp3')): shutil.copy(f, os.path.join(R, 'assets', 'voice'))
shutil.copy(T('audio', 'voice', 'blips.js'), os.path.join(R, 'src', 'blips.js'))
# art: environments (art team)
for f in glob.glob(T('art', '*.webp')):
    if os.path.getsize(f) > 0: shutil.copy(f, os.path.join(R, 'assets', 'art', 'bg'))
# battle FX: Frank (art/fx); music: Cody (audio/music, self-generated per README)
os.makedirs(os.path.join(R, 'assets', 'art', 'fx'), exist_ok=True)
for f in glob.glob(T('art', 'fx', '*.webp')): shutil.copy(f, os.path.join(R, 'assets', 'art', 'fx'))
man = load(T('art', 'manifest-environments.json'))
fxm = T('art', 'fx', 'manifest.json')
if os.path.exists(fxm):
    for k, v in load(fxm)['images'].items():
        if not v['src'].startswith('fx/'): v['src'] = 'fx/' + os.path.basename(v['src'])
        man['images'][k] = v
im = T('art', 'items', 'manifest-items.json')
if os.path.exists(im):
    os.makedirs(os.path.join(R, 'assets', 'art', 'icons'), exist_ok=True)
    for f in glob.glob(T('art', 'items', 'icons', '*.webp')): shutil.copy(f, os.path.join(R, 'assets', 'art', 'icons'))
    for k, v in load(im)['images'].items():
        if os.path.exists(os.path.join(R, 'assets', 'art', v['src'])): man['images'][k] = v
save(os.path.join(R, 'assets', 'art', 'manifest.json'), man)
os.makedirs(os.path.join(R, 'assets', 'music'), exist_ok=True)
for f in glob.glob(T('audio', 'music', '*.mp3')): shutil.copy(f, os.path.join(R, 'assets', 'music'))
shutil.copy(T('audio', 'music', 'manifest.json'), os.path.join(R, 'assets', 'music', 'manifest.json'))
print('integrated')
