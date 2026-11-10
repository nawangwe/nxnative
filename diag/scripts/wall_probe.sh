#!/bin/zsh
# One-shot: capture the diagnostic colour target, a pass dump and the wall draw's constant block + probe record from guest memory.
D=~/Games/OcarinaOfTime/diag-logs; L=~/Library/Logs/nxnative/0400486024DEC000.log
rm -f $D/cd/d10.raw $D/cd/shot10.png $D/mem/wall_cb1.bin $D/mem/wall_rec*.bin
n0=$(grep -c "^\[pass\]" $L)
printf 'coldump f4f7e695\npassdump 1\nshot %s/cd/shot10.png\n' "$D" >> $D/ctl.txt
for i in $(seq 1 30); do sleep 1; grep -q "coldump: frame" $L && [ -f $D/cd/shot10.png ] && [ "$(grep -c '^\[pass\]' $L)" -gt "$((n0+500))" ] && break; done; sleep 3
printf 'colsave %s/cd/d10.raw\n' "$D" >> $D/ctl.txt
F=$(grep -oE "^\[pass\] F[0-9]+" $L | tail -1 | sed 's/.*F//'); echo "frame $F"
python3 - "$L" "$F" "$D" <<'PY'
import re,sys
L,fr,D=sys.argv[1:4]; cur=None; found={}
for l in open(L,errors='replace'):
    m=re.match(r'\[pass\] F%s (\w) (\d+) (.*)'%fr,l.rstrip())
    if not m: continue
    k,p,rest=m.groups()
    if k=='K' and rest.startswith('st1'): cur=re.search(r'key=(\S{8})',rest)[1]
    if cur=='f4f7e695' and k=='B' and rest.startswith('st1'):
        for tag,pat in (('cb1',' cb reg1 '),('cb2',' cb reg2 '),('cb0',' cb reg0 '),('s0','sbufp reg0'),('s1','sbufp reg1')):
            if pat in rest and tag not in found: found[tag]=re.search(r'addr=(\S+)',rest)[1]
    if k=='j': cur=None
print(found)
if 'cb1' in found and 's0' in found:
    with open(D+'/ctl.txt','a') as f:
        f.write(f"memdump {found['cb1'][2:]} 256 {D}/mem/wall_cb1.bin\n")
        f.write(f"memdump {found['cb2'][2:]} 976 {D}/mem/wall_cb2.bin\n") if 'cb2' in found else None
        f.write(f"memdump {found['s1'][2:]} 128 {D}/mem/wall_s1.bin\n") if 's1' in found else None
    open(D+'/mem/wall_addrs.txt','w').write(repr(found))
PY
sleep 3
python3 - "$D" <<'PY'
import struct,sys,os
D=sys.argv[1]; found=eval(open(D+'/mem/wall_addrs.txt').read())
cb1=open(D+'/mem/wall_cb1.bin','rb').read(); words=struct.unpack('<64I',cb1)
y,z=words[8*4+1],words[8*4+2]  # c4[8].y, c4[8].z
print('c4[8].y = %#x  index %d flags %#x ; c4[8].z = %#x index %d flags %#x'%(y,y&0xFFFFF,y>>30,z,z&0xFFFFF,z>>30))
print('c4 rows 0-3 (model matrix):',[round(struct.unpack('<f',cb1[i*4:i*4+4])[0],3) for i in range(16)])
s1=open(D+'/mem/wall_s1.bin','rb').read() if os.path.exists(D+'/mem/wall_s1.bin') else b''
if s1: print('s1 words 12..24 (SH coeffs?):',[round(struct.unpack('<f',s1[i*4:i*4+4])[0],4) for i in range(12,25)])
# the records: need c5[46].w too (cb2? cb reg2 = c5) -> words
cb2=open(D+'/mem/wall_cb2.bin','rb').read() if os.path.exists(D+'/mem/wall_cb2.bin') else b''
if cb2:
    base=struct.unpack('<I',cb2[46*16+12:46*16+16])[0]; print('c5[46].w (record base) =',base)
    for name,idx in (('y',y&0xFFFFF),('z',z&0xFFFFF)):
        rec=(idx+base)<<5; print(f'record from c4[8].{name}: byte offset {rec} in s0 ({found["s0"]}) -> memdump')
        with open(D+'/ctl.txt','a') as f: f.write(f"memdump {int(found['s0'],16)+rec:x} 32 {D}/mem/wall_rec_{name}.bin\n")
PY
sleep 3
for n in y z; do f=~/Games/OcarinaOfTime/diag-logs/mem/wall_rec_$n.bin; [ -f $f ] && { printf "record %s: " $n; xxd -g4 $f | head -2; }; done
