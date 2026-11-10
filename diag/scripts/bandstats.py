import sys
import numpy as np
from PIL import Image
im = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(int)
nz = np.argwhere(im.sum(axis=2) > 30); y1, x1 = nz.max(axis=0) + 1
print('picture', x1, 'x', y1)
bw = x1 / 1536 * 96
print('band width on screen %.1f px' % bw)
for b in range(16):
    xs, xe = int(b * bw), int((b + 1) * bw)
    reg = im[int(y1*0.55):int(y1*0.95), xs:xe]
    m = reg.mean(axis=(0, 1)); s = reg.std(axis=(0, 1))
    print('band %2d (%-4s) x %4d-%4d mean %s std %s' % (b, ['real','lv0','fixS','lod'][b % 4], xs, xe, m.astype(int), s.astype(int)))
