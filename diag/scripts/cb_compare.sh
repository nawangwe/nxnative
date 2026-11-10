#!/bin/zsh
# After a DM_CTL "passdump 1" with DM_NVN_CBDUMP set: for every dumped uniform block of the ground colour shader (the copy the draw was given),
# dump the same bytes from the game's memory now and compare. Usage: cb_compare.sh <cbdump dir> <out dir>
D=${1:?cbdump dir}; O=${2:?out dir}; mkdir -p "$O"; C=~/Games/OcarinaOfTime/diag-logs/ctl.txt
ls "$D" | grep -E '_cb[0-9]+_0x[0-9a-f]+\.bin$' | tail -40 > "$O/list.txt"
while read f; do a=$(echo "$f" | sed -E 's/.*_cb[0-9]+_0x([0-9a-f]+)\.bin/\1/'); n=$(stat -f%z "$D/$f"); echo "memdump $a $n $O/mem_$f" >> "$C"; done < "$O/list.txt"
sleep 6
/usr/bin/python3 -I - "$D" "$O" <<'PY'
import sys, os
D,O=sys.argv[1:3]
for f in open(O+'/list.txt').read().split():
    a=open(os.path.join(D,f),'rb').read(); p=os.path.join(O,'mem_'+f)
    if not os.path.exists(p): print(f, 'no memdump'); continue
    b=open(p,'rb').read(); n=min(len(a),len(b)); diff=[i for i in range(n) if a[i]!=b[i]]
    print(f"{f}: {len(a)} bytes, {len(diff)} differ" + (f" (first at +{diff[0]:#x}, last +{diff[-1]:#x})" if diff else ""))
PY
