#!/bin/zsh
# With the plaid on screen: dump one frame's passes, find the texture IDs the ground colour draw (fs 2a712d1a) binds, and ask the host
# what object each ID is handed against the object its serial owns. Usage: texbind_probe.sh <out dir>
O=${1:?out dir}; mkdir -p "$O"; C=~/Games/OcarinaOfTime/diag-logs/ctl.txt; L=~/Library/Logs/nxnative/0400486024DEC000.log
n0=$(grep -c '^\[pass\]' "$L"); echo "shot $O/shot.png" >> "$C"; echo "passdump 1" >> "$C"
for i in $(seq 1 40); do sleep 1; [ "$(grep -c '^\[pass\]' "$L")" -gt $((n0 + 300)) ] && [ -f "$O/shot.png" ] && break; done; sleep 4
F=$(grep -oE '^\[pass\] F[0-9]+' "$L" | tail -1 | sed 's/.*F//'); echo "frame $F"
tids=$(awk -v f="$F" '$0 ~ "^\\[pass\\] F"f" "' "$L" | awk '/ K [0-9]+ st1 key=2a712d1a/{on=1} on && / B [0-9]+ st[01] tex reg[0-9]+ /{print $0} on && / d [0-9]+ .*fs=2a712d1a/{exit}' | grep -oE "tid=[0-9]+ real" | grep -oE "[0-9]+" | sort -un)
echo "texture IDs of the ground draw: $(echo $tids | tr '\n' ' ')"
m0=$(wc -l < "$L" | tr -d ' ')
for t in $tids; do echo "texbind $t" >> "$C"; done
sleep 5
sed -n "${m0},\$p" "$L" | grep "texbind tid=" | tee "$O/texbind.txt" | cut -c1-400
cp "$L" "$O/log.txt"
echo "--- bound object differs from the owner's texture:"; grep "texbind tid=" "$O/texbind.txt" | grep -E "bound is owner tex 0" | cut -c1-300 || echo "(none)"
