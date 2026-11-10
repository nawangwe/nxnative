#!/usr/bin/env python3
"""Decode a texraw/colsave dump of an RG11B10Float (Metal 92) or RGBA16F/RGBA32F target into float arrays. Usage: import rg11b10; rgb = rg11b10.load(path) -> (h, w, 3) float32"""
import numpy as np
def f11(x):  # 11-bit float: 5 exp bits, 6 mantissa, no sign
    e=(x>>6)&0x1f; m=x&0x3f
    v=np.where(e==0, (m/64.0)*2.0**-14, (1+m/64.0)*2.0**(e.astype(np.int32)-15)); v=np.where((e==31),np.where(m==0,np.inf,np.nan),v); return v.astype(np.float32)
def f10(x):
    e=(x>>5)&0x1f; m=x&0x1f
    v=np.where(e==0, (m/32.0)*2.0**-14, (1+m/32.0)*2.0**(e.astype(np.int32)-15)); v=np.where((e==31),np.where(m==0,np.inf,np.nan),v); return v.astype(np.float32)
def load(path):
    with open(path,'rb') as f:
        head=f.readline().decode().split(); w,h,fmt,row=map(int,head[:4]); raw=f.read()
    a=np.frombuffer(raw,np.uint8,row*h).reshape(h,row)
    if fmt==92:
        u=a[:, :w*4].copy().view(np.uint32).reshape(h,w)
        return np.dstack([f11(u&0x7ff), f11((u>>11)&0x7ff), f10((u>>22)&0x3ff)])
    if fmt==115: return a[:, :w*8].copy().view(np.float16).reshape(h,w,4)[..., :3].astype(np.float32)
    if fmt==125: return a[:, :w*16].copy().view(np.float32).reshape(h,w,4)[..., :3]
    raise SystemExit(f'format {fmt} not handled')
if __name__=='__main__':
    import sys; from PIL import Image
    rgb=load(sys.argv[1]); print(rgb.shape, 'min',np.nanmin(rgb),'max',np.nanmax(rgb),'nan',int(np.isnan(rgb).sum()))
    img=np.clip(rgb/ max(np.nanpercentile(rgb,99),1e-6),0,1)**(1/2.2)*255; Image.fromarray(img.astype(np.uint8)).save(sys.argv[1]+'.png'); print('saved',sys.argv[1]+'.png')
