#!/bin/zsh
# Around a save-reload: dump 2 frames every second for 25 s (tile generation passes), then list textures and dump the RG8 tile normal maps the ground draw reads.
D=~/Games/OcarinaOfTime/diag-logs/plaid-wrapv/sampfix/${1:-reload}; mkdir -p $D; C=~/Games/OcarinaOfTime/diag-logs/ctl.txt; L=~/Library/Logs/nxnative/0400486024DEC000.log
n0=$(grep -c "" $L)
for i in $(seq 1 25); do echo "passdump 2" >> $C; sleep 1; done; sleep 4
printf 'texlist 2\nshot %s/shot.png\n' $D >> $C; sleep 5
tail -n +$n0 $L > $D/log.txt
echo "frames dumped: $(grep -oE '^\[pass\] F[0-9]+' $D/log.txt | sort -u | wc -l)"
echo "--- 260x260 render-target attachments (P lines) in the dumped frames:"; grep -E " P [0-9]+ (c[0-9]|d) .*260x260" $D/log.txt | sed -E 's/^\[pass\] (F[0-9]+) P [0-9]+ (c[0-9]|d) ser=([0-9]+) fmt=([0-9]+).*/\1 \2 ser=\3 fmt=\4/' | sort | uniq -c | head -20
echo "--- 260x260 textures written by copies/clears/compute (X/C lines):"; grep -E "^\[pass\] F[0-9]+ [XC] .*260x260" $D/log.txt | cut -c1-160 | sort | uniq -c | head -10
echo "--- RG8 (fmt=30) maps bound to terrain colour draws:"; awk '/K [0-9]+ st1 key=2a712d1a/{f=1} f&&/ st1 tex reg[0-9]+ .*fmt=30 260x260/{print} /^\[pass\] F[0-9]+ [Dd] /{f=0}' $D/log.txt | grep -oE "tid=[0-9]+ real ser=[0-9]+" | sort | uniq -c
sers=$(awk '/K [0-9]+ st1 key=2a712d1a/{f=1} f&&/ st1 tex reg[0-9]+ .*fmt=30 260x260/{print} /^\[pass\] F[0-9]+ [Dd] /{f=0}' $D/log.txt | grep -oE "ser=[0-9]+" | sort -u | sed 's/ser=//')
for s in ${=sers}; do echo "texraw $s $D/n$s.raw 0" >> $C; done; sleep 8
echo "--- registered RG8 (format 0xd) 260x260 textures (texlist):"; grep "\[texlist\].*260x260x1 format 0xd" $L | tail -n 12 | sed -E 's/.*tid=([0-9]+) ser=([0-9]+).*storage (0x[0-9a-f]+).*/tid=\1 ser=\2 storage=\3/'
cd $D && ~/Games/OcarinaOfTime/venv/bin/python -I - <<'PY'
import glob, numpy as np
for f in sorted(glob.glob('n*.raw')):
    with open(f, 'rb') as fh:
        w, h, fmt, row = map(int, fh.readline().decode().split()[:4]); d = np.frombuffer(fh.read(), np.uint8, row * h).reshape(h, row)[:, :w * 2]
    print('%s: fmt %d zero texels %.1f%% R mean %.1f G mean %.1f distinct %d' % (f, fmt, 100 * (d.reshape(h, w, 2) == 0).all(axis=2).mean(), d[:, 0::2].mean(), d[:, 1::2].mean(), len(np.unique(d.reshape(-1, 2), axis=0))))
PY
