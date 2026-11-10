#!/bin/bash
# Watches the OoT host log for the GPU-mirror build (gpu_mirror_ok in nvn_mtl.m): every 60 s, the counts that tell whether the fix works and what it costs.
#   mirrored      GPU-drawn textures mirrored into their storage (first 4 + every 2000th are logged, so this is a floor)
#   budget-hit    textures left unmirrored because the frame's DM_NVN_GPU_MIRROR_MB was used (should stay 0)
#   first-use     "texture written by the CPU before its first use" (recreated tiles taken from storage: expected to rise as tiles come back)
#   sweep         last sweep line's GPU-only part (kept should fall toward 0: mirrored tiles are no longer GPU-only)
#   retired       memory-pressure retirements (0 on a 24 GB Mac)
#   RED           new [RED] lines since the start (listed)
LOG=~/Library/Logs/nxnative/0400486024DEC000.log
START=$(wc -l < "$LOG")
echo "monitor start: log at line $START, $(date +%H:%M:%S)"
while true; do
    sleep 60
    NOW=$(wc -l < "$LOG")
    S=$(tail -n +"$START" "$LOG")
    if ! pgrep -q -f "hybrid).app/Contents/MacOS/nxnative"; then echo "$(date +%H:%M:%S) host not running (log lines $NOW)"; fi
    M=$(grep -c "GPU-drawn texture mirrored into its storage" <<<"$S")
    B=$(grep -c "not mirrored into its storage: this frame" <<<"$S")
    F=$(grep -c "texture written by the CPU before its first use" <<<"$S")
    R=$(grep -c "shared textures: [0-9]* retired" <<<"$S")
    SW=$(grep "shared textures no texture object holds" <<<"$S" | tail -1 | sed 's/.*GPU-only: //')
    MEM=$(grep -E "^.*resident [0-9]+ MB" <<<"$S" | tail -1 | grep -oE "resident [0-9]+ MB.{0,60}" | head -1)
    FR=$(grep -oE "frame [0-9]+" <<<"$S" | tail -1)
    echo "$(date +%H:%M:%S) $FR | mirrored>=$M budget-hit=$B first-use=$F retired=$R | sweep GPU-only: ${SW:-none yet} | $MEM"
    grep "\[RED\]" <<<"$S" | grep -v "AV1\|av1\|texture type mismatch shader 9b310b\|made again over released storage" | sort | uniq -c | sort -rn | head -5 | sed 's/^/   RED: /'
done
