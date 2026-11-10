#!/usr/bin/env python3
"""Summarize DM_NVN_PASSDUMP lines ([pass] F<frame> <kind> <pass> ...) from the game log: per pass its attachments and draw count, then every texture sampled with its
shape, grouped, so the terrain's 260x260 tiles can be told apart. Usage: passdump_summary.py <log> [--frame N] [--size WxH]"""
import re, sys, collections

log = sys.argv[1]; want = None; size = None
if '--frame' in sys.argv: want = int(sys.argv[sys.argv.index('--frame') + 1])
if '--size' in sys.argv: size = sys.argv[sys.argv.index('--size') + 1]
passes = collections.OrderedDict(); tex = {}; frames = collections.Counter()
for l in open(log, errors='replace'):
    m = re.match(r'\[pass\] F(\d+) (\w) (\d+) (.*)', l.rstrip('\n'))
    if not m: continue
    f, kind, p, rest = int(m[1]), m[2], int(m[3]), m[4]
    frames[f] += 1
    if want is not None and f != want: continue
    P = passes.setdefault(p, {'frame': f, 'att': [], 'keys': collections.Counter(), 'draws': 0, 'tex': collections.OrderedDict(), 'clears': []})
    if kind == 'P': P['att'].append(rest)
    elif kind == 'C': P['clears'].append(rest)
    elif kind == 'K':
        P['keys'][rest] += 1
        if rest.startswith('st0') or rest.startswith('st1'): P['draws'] += rest.startswith('st1')   # one K per stage per draw: count fragment stages as draws
    elif kind == 'B':
        t = re.search(r'st(\d) tex reg(\d+) tid=(\d+) (\w+) ser=(\d+) fmt=(\d+) (\d+)x(\d+)x(\d+)', rest)
        if t:
            ser = int(t[5]); dims = f'{t[7]}x{t[8]}x{t[9]}'
            P['tex'].setdefault(ser, (dims, int(t[6]), t[4], int(t[1])))
            tex.setdefault(ser, (dims, int(t[6]), p))
print('frames with pass lines:', dict(sorted(frames.items())))
for p, P in passes.items():
    att = '; '.join(a[:70] for a in P['att'][:3])
    fs = [k for k in P['keys'] if k.startswith('st1')]
    print(f'pass {p} (F{P["frame"]}): draws~{P["draws"]}, {len(P["tex"])} textures, {len(fs)} fragment keys | {att}')
    if size:
        hit = [(s, v) for s, v in P['tex'].items() if v[0].startswith(size + 'x')]
        for s, v in hit: print(f'    {size} ser={s} fmt={v[1]} {v[2]} st{v[3]} dims={v[0]}')
by = collections.Counter((v[0], v[1]) for v in tex.values())
print('\ntextures sampled, by shape:'); [print(f'  {n:5} {d} fmt={f}') for (d, f), n in by.most_common(25)]
