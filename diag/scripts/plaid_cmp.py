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
