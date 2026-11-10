#!/usr/bin/env python3
"""Compare a texture as the GPU holds it (DM_CTL texraw dump) with the game's own copy in guest memory (DM_CTL memdump of its storage, NVN block-linear).
Usage: cmp_storage.py <texraw file> <memdump file> <bytes per texel> <block height log2> [layer]
Prints how many texels differ and saves <memdump>_gpu.png / <memdump>_guest.png / <memdump>_diff.png for a look."""
import sys
import numpy as np
from PIL import Image

raw, mem, bpt, bhl = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]); layer = int(sys.argv[5]) if len(sys.argv) > 5 else 0
with open(raw, 'rb') as f:
    head = f.readline().decode().split(); w, h, fmt, row = map(int, head[:4]); ns = int(head[4]) if len(head) > 4 else 1
    data = f.read()
sz = row * h
gpu = np.frombuffer(data, np.uint8, sz, sz * layer).reshape(h, row)[:, :w * bpt].copy()
g = np.fromfile(mem, np.uint8)
bh = 1 << bhl                       # GOBs per block
wb = w * bpt; gobs_w = (wb + 63) // 64; rows_pad = ((h + 8 * bh - 1) // (8 * bh)) * 8 * bh
layer_bytes = gobs_w * 64 * rows_pad
g = g[layer * layer_bytes:(layer + 1) * layer_bytes]
if len(g) < layer_bytes: print(f'guest dump too short: {len(g)} < {layer_bytes}'); sys.exit(1)
# block-linear (Tegra): 64 B x 8 row GOBs, bh GOBs stacked per block, blocks row-major
ys, xs = np.mgrid[0:h, 0:wb]
gob_x = xs // 64; gob_y = ys // 8; blk_y = gob_y // bh; gob_in = gob_y % bh
xi = xs % 64; yi = ys % 8
off = (xi % 16) | (yi & 1) << 4 | ((yi >> 1) & 1) << 5 | ((xi >> 4) & 1) << 6 | ((yi >> 2) & 1) << 7 | ((xi >> 5) & 1) << 8   # Tegra GOB bit order, found by matching the GPU copy of a height tile
addr = (blk_y * gobs_w + gob_x) * (512 * bh) + gob_in * 512 + off
guest = g[addr]
diff = (gpu != guest)
tex_diff = diff.reshape(h, w, bpt).any(axis=2)
print(f'{raw} vs {mem} layer {layer}: {tex_diff.sum()} of {w*h} texels differ ({tex_diff.mean():.1%}); guest non-zero texels {np.any(guest.reshape(h,w,bpt)!=0,axis=2).mean():.1%}, gpu {np.any(gpu.reshape(h,w,bpt)!=0,axis=2).mean():.1%}')
for name, a in (('gpu', gpu), ('guest', guest)):
    t = a.reshape(h, w, bpt)
    img = t[..., 0] if bpt == 1 else t[..., :3] if bpt >= 3 else np.dstack([t[..., 0], t[..., 1], np.zeros_like(t[..., 0])])
    Image.fromarray(img).save(f'{mem}_{name}.png')
Image.fromarray((tex_diff * 255).astype(np.uint8)).save(f'{mem}_diff.png')
