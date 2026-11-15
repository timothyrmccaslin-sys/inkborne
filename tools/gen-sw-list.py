#!/usr/bin/env python3
"""Regenerate the SHELL/EXTRA precache lists in sw.js from the tree. Run before every release."""
import os, re, glob, json
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(R)
shell = ['./', 'index.html', 'style.css', 'manifest.json'] + sorted(glob.glob('src/**/*.js', recursive=True)) + \
  ['pkg/inkborne_core.js', 'pkg/inkborne_core_bg.wasm'] + sorted(glob.glob('data/**/*.json', recursive=True)) + sorted(glob.glob('fonts/*.woff2')) + ['assets/art/manifest.json']
extra = sorted(glob.glob('assets/icons/*.png')) + sorted('assets/art/' + v['src'] for v in json.load(open('assets/art/manifest.json'))['images'].values()) + \
  sorted(glob.glob('assets/sfx/*.mp3') + glob.glob('assets/voice/*.mp3') + glob.glob('assets/music/*.mp3')) + ['assets/music/manifest.json']
fmt = lambda xs: '[\n' + ''.join(f"  '{x}',\n" for x in xs) + ']'
s = open('sw.js').read()
s = re.sub(r"const SHELL = \[.*?\n\];", 'const SHELL = ' + fmt(shell) + ';', s, flags=re.S)
s = re.sub(r"const EXTRA = \[.*?\n\];", 'const EXTRA = ' + fmt(extra) + ';', s, flags=re.S)
open('sw.js', 'w').write(s); print(len(shell), 'shell', len(extra), 'extra')
