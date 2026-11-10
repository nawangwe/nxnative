#!/bin/zsh
# Live probe for the plaid ground: with the game in front and the plaid on screen, dump one frame's passes, then for every 260x260 terrain
# map bound in that frame save the GPU copy (texraw) and the game's own copy (memdump of its storage) and compare them texel by texel.
# Usage: plaid_probe.sh <out dir>
set -u
O=${1:?out dir}; mkdir -p "$O"
C=~/Games/OcarinaOfTime/diag-logs/ctl.txt; L=~/Library/Logs/nxnative/0400486024DEC000.log
n0=$(grep -c '^\[pass\]' "$L")
printf 'shot %s/shot.png\ntexlist 1\ntexlist 4\npassdump 1\n' "$O" >> "$C"
for i in $(seq 1 40); do sleep 1; n=$(grep -c '^\[pass\]' "$L"); [ "$n" -gt $((n0 + 300)) ] && [ -f "$O/shot.png" ] && break; done; sleep 4
cp "$L" "$O/log-at-probe.txt"; F=$(grep -oE '^\[pass\] F[0-9]+' "$L" | tail -1 | sed 's/.*F//'); echo "frame $F, $(($(grep -c '^\[pass\]' "$L") - n0)) pass lines"
/usr/bin/python3 -I - "$L" "$F" "$O" "$C" <<'PY'
import re, sys
L, F, O, C = sys.argv[1:5]
maps = {}; reg = {}
for l in open(L, errors='replace'):
    m = re.match(r'\[pass\] F%s B (\d+) st(\d) tex reg(\d+) tid=(\d+) real ser=(\d+) fmt=(\d+) (\d+)x(\d+)x(\d+) view_lv=(\d+)\+(\d+) view_sl=(\d+) array=(\d+) target=(\d+)' % F, l)
    if m and m.group(7) == '260' and m.group(8) == '260':
        ser = int(m.group(5)); maps.setdefault(ser, (int(m.group(6)), int(m.group(10)), int(m.group(12)), 'p%s st%s' % (m.group(1), m.group(2))))
    t = re.match(r'.*\[texlist\] tid=(\d+) ser=(\d+) target (\d+) (\d+)x(\d+)x(\d+) format (0x[0-9a-f]+) levels (\d+) flags (\S+) storage (0x[0-9a-f]+) size (0x[0-9a-f]+) block height/depth log2 (\d+)/(\d+)', l)
    if t: reg[int(t.group(2))] = dict(w=int(t.group(4)), h=int(t.group(5)), d=int(t.group(6)), nfmt=t.group(7), levels=int(t.group(8)), mem=t.group(10), size=int(t.group(11), 16), bhl=int(t.group(12)))
print(len(maps), '260x260 textures bound in the frame;', len(reg), 'registered textures listed')
with open(C, 'a') as c, open(O + '/maps.tsv', 'w') as o:
    for ser, (fmt, lv, arr, where) in sorted(maps.items()):
        r = reg.get(ser)
        c.write('texraw %d %s/t%d.raw 0\n' % (ser, O, ser))
        if r: c.write('memdump %s %d %s/t%d.mem\n' % (r['mem'][2:], r['size'], O, ser))
        o.write('%d\t%d\t%d\t%d\t%s\t%s\t%s\t%d\t%d\n' % (ser, fmt, lv, arr, where, r['mem'] if r else '-', r['nfmt'] if r else '-', r['size'] if r else 0, r['bhl'] if r else -1))
        print(ser, 'mtl fmt', fmt, 'levels', lv, 'array', arr, where, 'storage', r['mem'] if r else 'not in texlist', 'nvn fmt', r['nfmt'] if r else '-', 'bhl', r['bhl'] if r else '-')
PY
sleep 6
ls "$O" | wc -l
echo "--- compare GPU copy with the game's copy (level 0, layer 0)"
/usr/bin/python3 -I - "$O" <<'PY'
import sys, os, struct
import numpy as np
O = sys.argv[1]
BC8 = {130, 131, 140, 141}; BC16 = {132, 133, 134, 135, 142, 143, 150, 151, 152, 153}
BPP = {70: 4, 71: 4, 30: 2, 31: 2, 55: 4, 53: 4, 54: 4, 25: 2, 20: 2, 10: 1, 13: 1, 115: 8, 92: 4, 65: 4, 105: 8, 125: 16}
def gob_addr(w_b, h, bh, xs, ys):   # Tegra block-linear: 64 B x 8 row GOBs, bh GOBs per block
    gobs_w = (w_b + 63) // 64
    gob_x = xs // 64; gob_y = ys // 8; blk_y = gob_y // bh; gob_in = gob_y % bh
    xi = xs % 64; yi = ys % 8
    off = (xi % 16) | (yi & 1) << 4 | ((yi >> 1) & 1) << 5 | ((xi >> 4) & 1) << 6 | ((yi >> 2) & 1) << 7 | ((xi >> 5) & 1) << 8
    return (blk_y * gobs_w + gob_x) * (512 * bh) + gob_in * 512 + off
for line in open(O + '/maps.tsv'):
    ser, fmt, lv, arr, where, mem, nfmt, size, bhl = line.rstrip('\n').split('\t'); ser = int(ser); fmt = int(fmt); bhl = int(bhl)
    raw, memf = '%s/t%d.raw' % (O, ser), '%s/t%d.mem' % (O, ser)
    if not os.path.exists(raw): print(ser, 'no GPU dump'); continue
    with open(raw, 'rb') as f:
        head = f.readline().decode().split(); w, h, mfmt, row = map(int, head[:4]); ns = int(head[4]) if len(head) > 4 else 1
        data = f.read()
    if mfmt in BC8 or mfmt in BC16: bpt = 8 if mfmt in BC8 else 16; wt, ht = (w + 3) // 4, (h + 3) // 4
    elif mfmt in BPP: bpt = BPP[mfmt]; wt, ht = w, h
    else: print(ser, 'format', mfmt, 'not handled'); continue
    gpu = np.frombuffer(data, np.uint8, row * ht, 0).reshape(ht, row)[:, :wt * bpt]
    info = '%s %dx%d mtl fmt %d (%d B/texel-or-block) layers %s levels %s %s' % (ser, w, h, mfmt, bpt, arr, lv, where)
    if not os.path.exists(memf) or bhl < 0: print(info, '| no guest dump'); continue
    g = np.fromfile(memf, np.uint8); bh = 1 << bhl; w_b = wt * bpt
    ys, xs = np.mgrid[0:ht, 0:w_b]
    addr = gob_addr(w_b, ht, bh, xs, ys)
    if addr.max() >= len(g): print(info, '| guest dump too short (%d < %d)' % (len(g), addr.max() + 1)); continue
    guest = g[addr]
    diff = (gpu != guest).reshape(ht, wt, bpt).any(axis=2)
    nz_g = np.any(gpu.reshape(ht, wt, bpt) != 0, axis=2).mean(); nz_m = np.any(guest.reshape(ht, wt, bpt) != 0, axis=2).mean()
    flag = '  <<< DIFFERS' if diff.mean() > 0.001 else ''
    print('%s | %d of %d texels differ (%.1f%%); non-zero gpu %.0f%% guest %.0f%%%s' % (info, diff.sum(), wt * ht, 100 * diff.mean(), 100 * nz_g, 100 * nz_m, flag))
    np.save('%s/t%d.diff.npy' % (O, ser), diff)
PY
