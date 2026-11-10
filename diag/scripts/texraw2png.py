#!/usr/bin/env python3
"""Turn a DM_CTL texraw dump (header: width height metal_format bytes_per_row [slices]; then raw slices at 16 bytes a texel row stride) into PNGs, one per slice.
Usage: texraw2png.py <dump> [<dump>...]  -> <dump>_s<slice>.png, and a one-line summary per slice (min/max/mean per channel, fraction of zero texels)."""
import sys, struct
import numpy as np
from PIL import Image

# Metal pixel format -> (numpy dtype, channels)
FMT = {252: ('f4', 1), 250: ('f2', 1), 92: ('u4', 1), 115: ('f2', 4), 10: ('u1', 1), 11: ('u1', 1), 12: ('i1', 1), 13: ('u1', 1), 14: ('i1', 1), 20: ('u2', 1), 22: ('i2', 1), 23: ('u2', 1), 24: ('i2', 1), 25: ('f2', 1),
       30: ('u1', 2), 31: ('u1', 2), 32: ('i1', 2), 33: ('u1', 2), 34: ('i1', 2), 53: ('u4', 1), 54: ('i4', 1), 55: ('f4', 1), 60: ('u2', 2), 62: ('i2', 2), 63: ('u2', 2), 64: ('i2', 2), 65: ('f2', 2),
       70: ('u1', 4), 71: ('u1', 4), 72: ('i1', 4), 73: ('u1', 4), 74: ('i1', 4), 80: ('u1', 4), 81: ('u1', 4), 103: ('u4', 2), 104: ('i4', 2), 105: ('f4', 2),
       110: ('u2', 4), 112: ('i2', 4), 113: ('u2', 4), 114: ('i2', 4), 115: ('f2', 4), 123: ('u4', 4), 124: ('i4', 4), 125: ('f4', 4)}


def main(path):
    with open(path, 'rb') as f:
        head = f.readline().decode().split()
        w, h, fmt, row = map(int, head[:4]); ns = int(head[4]) if len(head) > 4 else 1
        raw = f.read()
    if fmt not in FMT:
        print(f'{path}: {w}x{h} Metal format {fmt}: not a plain texel format I know (compressed or depth); first bytes {raw[:16].hex()}'); return
    dt, nc = FMT[fmt]
    sz = row * h
    for s in range(ns):
        a = np.frombuffer(raw, dtype=np.uint8, count=sz, offset=sz * s).reshape(h, row)
        tex = a[:, :w * nc * np.dtype(dt).itemsize].copy().view(dt).reshape(h, w, nc).astype(np.float32)
        zero = float((np.abs(tex).sum(axis=2) == 0).mean())
        stats = ' '.join(f'c{i}:{tex[..., i].min():.3g}..{tex[..., i].max():.3g}~{tex[..., i].mean():.3g}' for i in range(nc))
        nan = int(np.isnan(tex).sum())
        print(f'{path} slice {s}: {w}x{h} fmt {fmt} ch {nc}: {stats}; zero texels {zero:.1%}' + (f'; NaN values {nan}' if nan else ''))
        img = tex.copy()
        if dt in ('f2', 'f4'):
            lo, hi = np.nanpercentile(img, 1), np.nanpercentile(img, 99)
            img = (np.nan_to_num(img) - lo) / (hi - lo if hi > lo else 1) * 255
        elif dt in ('u2', 'i2'): img = img / 257.0
        elif dt in ('u4', 'i4'): img = img / 16843009.0
        elif dt == 'i1': img = img + 128
        img = np.clip(img, 0, 255).astype(np.uint8)
        if nc == 1: im = Image.fromarray(img[..., 0], 'L')
        elif nc == 2: im = Image.fromarray(np.dstack([img[..., 0], img[..., 1], np.zeros_like(img[..., 0])]), 'RGB')
        elif nc == 3: im = Image.fromarray(img, 'RGB')
        else: im = Image.fromarray(img[..., :3] if fmt not in (80, 81) else img[..., [2, 1, 0]], 'RGB')
        im.save(f'{path}_s{s}.png')


for p in sys.argv[1:]: main(p)
