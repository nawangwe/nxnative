#!/usr/bin/env python3
"""Summarise a DM_NVN_PASSDUMP (PASSDUMP_ALL) dump from nvn_replay / the host.
Usage: parse_pd.py <passdump.txt>                 -> one line per pass: targets, draw counts, distinct fragment-stage textures
       parse_pd.py <passdump.txt> <pass> [<pass>]  -> every draw of those passes with its shader keys and the textures bound per stage
Lines: '[pass] F<frame> <letter> <pass> ...'; P = attachment, D/m = draw, K = stage key, B ... tex = texture binding, T = bind (tid/sid/ser)."""
import re, sys
from collections import OrderedDict, defaultdict

passes = OrderedDict()   # pass index -> dict(targets=[], draws=[], frame)
cur_keys = {}            # stage -> key (sticky until changed)
cur_tex = defaultdict(dict)   # stage -> reg -> text (sticky)
lastp = None

def P(i):
    if i not in passes: passes[i] = {'targets': [], 'draws': [], 'events': []}
    return passes[i]

rx = re.compile(r'^\[pass\] F(\d+) (\S) (\d+) ?(.*)$')
for line in open(sys.argv[1], errors='replace'):
    m = rx.match(line.rstrip('\n'))
    if not m: continue
    frame, kind, pi, rest = m.group(1), m.group(2), int(m.group(3)), m.group(4)
    if kind == 'P':
        P(pi)['targets'].append(rest)
    elif kind == 'K':
        mm = re.match(r'st(\d) key=(\S+)', rest)
        if mm: cur_keys[int(mm.group(1))] = mm.group(2)
    elif kind == 'B':
        mm = re.match(r'st(\d) tex reg(\d+) (.*)$', rest)
        if mm: cur_tex[int(mm.group(1))][int(mm.group(2))] = mm.group(3)
    elif kind in ('D', 'd', 'm'):
        P(pi)['draws'].append({'kind': kind, 'text': rest, 'keys': dict(cur_keys), 'tex': {s: dict(r) for s, r in cur_tex.items()}})
    elif kind in ('C', 'E', 'N', 'L'):
        P(pi)['events'].append(kind + ' ' + rest[:80])

def texsum(d, stage):
    return [(int(re.search(r'tid=(\d+)', t).group(1)), re.search(r'ser=(\d+)', t).group(1), re.search(r'fmt=(\d+) (\d+x\d+x\d+)', t).groups()) for t in d['tex'].get(stage, {}).values()]

if len(sys.argv) == 2:
    for pi, p in passes.items():
        cols = [t for t in p['targets'] if re.match(r'c\d', t)]
        depth = [t for t in p['targets'] if t.startswith('d ')]
        tg = '; '.join(re.sub(r' mtl=\S+', '', c) for c in cols[:2]) + (' +%d' % (len(cols) - 2) if len(cols) > 2 else '')
        kinds = defaultdict(int)
        for d in p['draws']: kinds[d['kind']] += 1
        fs = set()
        for d in p['draws']:
            k = d['keys'].get(1)
            if k: fs.add(k[:8])
        print(f"pass {pi:3d}: draws {dict(kinds)} fs keys {len(fs)}  targets: {tg or '-'}{'  depth' if depth else ''}")
else:
    want = set(int(a) for a in sys.argv[2:])
    for pi, p in passes.items():
        if pi not in want: continue
        print(f"=== pass {pi}")
        for t in p['targets']: print('  target', re.sub(r' mtl=\S+', '', t))
        for e in p['events'][:6]: print('  event', e)
        for n, d in enumerate(p['draws']):
            keys = ' '.join(f"st{s}={k}" for s, k in sorted(d['keys'].items()) if s in (0, 1) or d['kind'] == 'm')
            print(f"  draw {n:3d} {d['kind']} {d['text'][:110]}")
            print(f"           keys {keys}")
            for s in sorted(d['tex']):
                if s == 5: continue
                for reg, t in sorted(d['tex'][s].items()):
                    tt = re.sub(r' mtl=\S+', '', t)[:150]
                    print(f"           st{s} reg{reg}: {tt}")
