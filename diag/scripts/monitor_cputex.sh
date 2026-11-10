#!/bin/zsh
# Events: host start, trace health, suspicious first-use decisions (CPU-filled 260x260 maps resolved as plain GPU textures), sweep lines, heartbeat
L=~/Library/Logs/nxnative/0400486024DEC000.log
for i in {1..600}; do pgrep -x dmhost >/dev/null && break; sleep 1; done
pgrep -x dmhost >/dev/null || { echo "host did not start within 10 min"; exit 0; }
echo "host started (pid $(pgrep -x dmhost))"
sleep 5
n0=$(grep -c "\[cputex\]" $L); echo "trace lines so far: $n0"
last=$(date +%s); seen=0; zs=0
tail -F -n0 $L 2>/dev/null | while IFS= read -r line; do
  case "$line" in
    *"[cputex] first use"*"fmt 0xa "*"GPU TEXTURE"*"mem_any 1"*|*"[cputex] first use"*"fmt 0x25 "*"GPU TEXTURE"*"mem_any 1"*) echo "SUSPECT (filled map left as GPU texture): ${line:0:900}";;
    *"[cputex] first use"*"fmt 0xa "*"GPU TEXTURE"*|*"[cputex] first use"*"fmt 0x25 "*"GPU TEXTURE"*) zs=$((zs+1));;
    *"[cputex] first use"*) seen=$((seen+1)); [[ $seen -le 3 ]] && echo "sample: ${line:0:400}";;
    *"alias sweep"*|*"queued for a write-back"*) echo "sweep: ${line:0:300}";;
    *"[RED]"*|*"Metal error"*|*"GPU error"*|*"crash"*) echo "ERR: ${line:0:300}";;
  esac
  now=$(date +%s)
  if (( now - last >= 900 )); then last=$now; echo "heartbeat: $(grep -c '\[cputex\] first use' $L) first-use traces, $zs zero-storage maps left to the later-write path, $(grep -c 'GPU TEXTURE' $L) resolved as GPU textures, $(grep -c 'registered ser' $L) registrations; $(grep 'resident' $L | tail -1 | cut -c1-120)"; fi
  pgrep -x dmhost >/dev/null || { echo "host exited"; exit 0; }
done
