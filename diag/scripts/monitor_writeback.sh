#!/bin/zsh
# Monitor for the write-back build: one line when something notable happens, a heartbeat every 10 min. Events: write-back let-go lines, sweep passes, memory, zero normal maps (nm_check), new [RED] lines.
L=~/Library/Logs/nxnative/0400486024DEC000.log; [ -s $L ] || L=~/Library/Logs/nxnative/0400486024DEC000.prev.log
D=~/Games/OcarinaOfTime/diag-logs/plaid-wrapv/sampfix; wb0=0; sw0=0; red0=$(grep -c "\[RED\]" $L); t0=$(date +%s); last_hb=$t0; last_nm=$t0; n=0
while pgrep -f dmhost >/dev/null; do
  sleep 30; now=$(date +%s); n=$((n+1))
  wb=$(grep -c "written back into their storage and let go" $L); sw=$(grep -c "queued for a write-back" $L); red=$(grep -c "\[RED\]" $L)
  fr=$(grep -oE 'up to frame [0-9]+' $L | tail -1 | grep -oE '[0-9]+')
  if [ "$wb" -gt "$wb0" ]; then grep "written back into their storage and let go" $L | tail -1 | sed -E 's/.*\] (shared textures written back.*)/WRITEBACK: \1/' | cut -c1-200; wb0=$wb; fi
  if [ "$red" -gt "$red0" ]; then grep "\[RED\]" $L | tail -n $((red - red0)) | grep -v "AV1" | cut -c1-180 | sed 's/^/RED: /'; red0=$red; fi
  if [ $((now - last_nm)) -ge 300 ]; then last_nm=$now; out=$($D/nm_check.sh "wb_$(date +%H%M)" 2>&1 | grep -E "zero texels|no ground" | tr '\n' ' '); case "$out" in *"zero texels 100"*|*"zero texels [5-9][0-9]"*) echo "ZERO MAP: $out";; *) echo "maps ok (frame $fr): $(echo $out | cut -c1-120)";; esac; fi
  if [ $((now - last_hb)) -ge 600 ]; then last_hb=$now; m=$(grep "memory up to frame" $L | tail -1 | sed -E 's/.*resident ([0-9]+) MB, GPU allocated ([0-9]+) MB.*shared textures ([0-9]+) \(([0-9]+) of them unreferenced.*/resident \1 MB, GPU \2 MB, shared \3 (\4 unreferenced)/'); s=$(grep "queued for a write-back" $L | tail -1 | sed -E 's/.*holds: ([0-9]+), ([0-9]+) MB; ([0-9]+) of them swept.*GPU-only: ([0-9]+) queued for a write-back, ([0-9]+) kept \(([0-9]+) MB of ([0-9]+) MB budget\), ([0-9]+) evicted.*/orphans \1 (\2 MB) swept \3 | wb-queued \4 kept \5 (\6 of \7 MB) evicted \8/'); echo "HEARTBEAT frame $fr ($((fr/3600)) min): $m; last sweep: $s; write-back lines $wb"; fi
done
echo "host exited (frame $fr)"
