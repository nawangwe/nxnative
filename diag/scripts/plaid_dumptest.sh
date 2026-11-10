#!/bin/zsh
# At a plaid moment: shot (stripe 1 = bound-sampler sample), then a pass-dump frame with a shot in that same frame (pass dump re-encodes every argument block), then a shot right after.
D=~/Games/OcarinaOfTime/diag-logs/plaid-wrapv/sampfix; C=~/Games/OcarinaOfTime/diag-logs/ctl.txt; L=~/Library/Logs/nxnative/0400486024DEC000.prev.log
n0=$(grep -c "" $L)
printf 'shot %s/after.png\n' $D >> $C; for i in $(seq 1 20); do [ -s $D/after.png ] && break; sleep 1; done; sleep 1
printf 'passdump 1\nshot %s/dump.png\n' $D >> $C; for i in $(seq 1 30); do [ -s $D/dump.png ] && break; sleep 1; done; sleep 3
printf 'shot %s/after2.png\nsampinfo 401\n' $D >> $C; for i in $(seq 1 20); do [ -s $D/after2.png ] && break; sleep 1; done; sleep 2
tail -n +$n0 $L > $D/log-dumptest.txt; ls -la $D/*.png; grep "\[sampinfo\]" $D/log-dumptest.txt | head -3 | cut -c1-240
echo "args stats:"; grep -oE "args (reuse|enc|cb)[^,;]*" $L | tail -3
cd $D && for f in after dump after2; do ~/Games/OcarinaOfTime/venv/bin/python -I bandstats.py $f.png | grep -E "band  ?(8|9|10|12|13|14) " | tr '\n' ' '; echo " <- $f"; done
~/Games/OcarinaOfTime/venv/bin/python -I - <<'PY'
from PIL import Image
ims = [Image.open(f + '.png').convert('RGB').crop((960, 560, 1920, 1080)) for f in ('before', 'after', 'dump', 'after2')]
out = Image.new('RGB', (960 * 2 + 10, 520 * 2 + 10), (255, 0, 255))
for i, im in enumerate(ims): out.paste(im, ((i % 2) * 970, (i // 2) * 530))
out.save('cmp_dumptest.png'); print('cmp_dumptest.png: before | after / dump | after2 (x 960-1920, y 560-1080)')
PY
