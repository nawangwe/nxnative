#!/usr/bin/env python3
"""Build the comparison page: method A (keep small GPU-only orphans) from its 62-min session log, method B (write-back) from the current log."""
import re, json, sys, os
def parse(path):
    mem, sw, wb = [], [], []; frame = 0
    for line in open(path, errors='replace'):
        m = re.search(r'memory up to frame (\d+): resident (\d+) MB, GPU allocated (\d+) MB.*shared textures (\d+) \((\d+) of them unreferenced', line)
        if m: frame = int(m.group(1)); mem.append(dict(frame=frame, resident=int(m.group(2)), gpu=int(m.group(3)), shared=int(m.group(4)), unref=int(m.group(5)))); continue
        m = re.search(r'up to frame (\d+)', line)
        if m: frame = max(frame, int(m.group(1)))
        m = re.search(r'holds: (\d+), (\d+) MB; (\d+) of them swept, (\d+) MB.*?(\d+)(?: small GPU-only ones)? kept', line)
        if m: sw.append(dict(frame=frame, orphans=int(m.group(1)), orph_mb=int(m.group(2)), swept=int(m.group(3)), swept_mb=int(m.group(4)), kept=int(m.group(5)))); continue
        m = re.search(r'written back into their storage and let go: (\d+) now, (\d+) so far \((\d+) MB\)', line)
        if m: wb.append(dict(frame=frame, total=int(m.group(2)), mb=int(m.group(3))))
    return dict(mem=mem, sweeps=sw, wb=wb)
A = parse(os.path.expanduser('~/Games/OcarinaOfTime/diag-logs/plaid-wrapv/sampfix/session-sweepfix2-full.log'))
L = os.path.expanduser('~/Library/Logs/nxnative/0400486024DEC000.log')
if not os.path.getsize(L): L = os.path.expanduser('~/Library/Logs/nxnative/0400486024DEC000.prev.log')
B = parse(L)
out = sys.argv[1]
tpl = open(os.path.expanduser('~/Games/OcarinaOfTime/diag-logs/plaid-wrapv/sampfix/compare_template.html')).read()
open(out, 'w').write(tpl.replace('__DATA__', json.dumps(dict(A=A, B=B), separators=(',', ':'))))
print('A: %d mem rows to frame %d; B: %d mem rows to frame %d, %d write-back lines' % (len(A['mem']), A['mem'][-1]['frame'] if A['mem'] else 0, len(B['mem']), B['mem'][-1]['frame'] if B['mem'] else 0, len(B['wb'])))
