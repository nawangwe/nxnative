#!/bin/zsh
# Dump the RG8 tile normal maps bound to the ground draws in one frame and report how much of each is zero (the plaid state = 100% zero).
D=~/Games/OcarinaOfTime/diag-logs/plaid-wrapv/sampfix/${1:-nmcheck}; mkdir -p $D; C=~/Games/OcarinaOfTime/diag-logs/ctl.txt; L=~/Library/Logs/nxnative/0400486024DEC000.log; [ -s $L ] || L=~/Library/Logs/nxnative/0400486024DEC000.prev.log
n0=$(grep -c "" $L); echo "passdump 1" >> $C; for i in $(seq 1 15); do sleep 1; [ $(grep -c "" $L) -gt $((n0 + 20000)) ] && break; done; sleep 3
sers=$(tail -n +$n0 $L | awk '/K [0-9]+ st1 key=2a712d1a/{f=1} f&&/ st1 tex reg[0-9]+ .*fmt=30 260x260/{print} /^\[pass\] F[0-9]+ [Dd] /{f=0}' | grep -oE "ser=[0-9]+" | sort -u | sed 's/ser=//')
[ -z "$sers" ] && { echo "no ground draws in the dumped frame (frame $(grep -oE 'up to frame [0-9]+' $L | tail -1))"; exit 0; }
for s in ${=sers}; do echo "texraw $s $D/n$s.raw 0" >> $C; done; sleep 6
cd $D && ~/Games/OcarinaOfTime/venv/bin/python -I - <<'PY'
import glob, numpy as np
for f in sorted(glob.glob('n*.raw')):
    with open(f, 'rb') as fh:
        w, h, fmt, row = map(int, fh.readline().decode().split()[:4]); d = np.frombuffer(fh.read(), np.uint8, row * h).reshape(h, row)[:, :w * 2]
    a = d.reshape(h, w, 2); print('%s: zero texels %.1f%%, distinct %d' % (f, 100 * (a == 0).all(axis=2).mean(), len(np.unique(a.reshape(-1, 2), axis=0))))
PY
