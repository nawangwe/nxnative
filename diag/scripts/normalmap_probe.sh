#!/bin/zsh
# Every 45 s: dump one frame's passes; once terrain colour draws bind 260x260 RG8 (fmt 30) tile normal maps, texraw them and report how much of each is zero. Stops after the first success.
D=~/Games/OcarinaOfTime/diag-logs/plaid-wrapv/sampfix/${1:-clean}; mkdir -p $D; C=~/Games/OcarinaOfTime/diag-logs/ctl.txt; L=~/Library/Logs/nxnative/0400486024DEC000.prev.log
for try in $(seq 1 40); do
  n0=$(grep -c "" $L); echo "passdump 1" >> $C; sleep 6
  sers=$(tail -n +$n0 $L | awk '/K [0-9]+ st1 key=2a712d1a/{f=1} f&&/ st1 tex reg[0-9]+ .*fmt=30 260x260/{print} /^\[pass\] F[0-9]+ [Dd] /{f=0}' | grep -oE "ser=[0-9]+" | sort -u | sed 's/ser=//')
  if [ -n "$sers" ]; then
    echo "shot $D/shot.png" >> $C
    for s in $sers; do echo "texraw $s $D/n$s.raw 0" >> $C; done; sleep 6
    tail -n +$n0 $L > $D/log.txt
    ~/Games/OcarinaOfTime/venv/bin/python -I - $D <<'PY'
import sys, glob, numpy as np
for f in sorted(glob.glob(sys.argv[1] + '/n*.raw')):
    with open(f, 'rb') as fh:
        w, h, fmt, row = map(int, fh.readline().decode().split()[:4]); d = np.frombuffer(fh.read(), np.uint8, row * h).reshape(h, row)[:, :w * 2]
    print('%s: %dx%d fmt %d: zero texels %.1f%%, R mean %.1f G mean %.1f, distinct %d' % (f.split('/')[-1], w, h, fmt, 100 * (d.reshape(h, w, 2) == 0).all(axis=2).mean(), d[:, 0::2].mean(), d[:, 1::2].mean(), len(np.unique(d.reshape(-1, 2), axis=0))))
PY
    exit 0
  fi
  sleep 39
done
echo "no terrain draws seen in 40 tries"
