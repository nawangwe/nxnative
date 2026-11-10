import re,sys
# backward slice of an MSL function body for given variables (SPIRV-Cross style straight-line code)
path,lo,hi=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]); targets=set(sys.argv[4:])
lines=open(path).read().split('\n')[lo-1:hi]
defs={}
for i,l in enumerate(lines):
    m=re.match(r'\s*(?:float\d?|int|uint|bool|half\d?)?\s*(_\d+|[a-zA-Z_]\w*(?:\.\w+)?)\s*=\s*(.*);',l)
    if m: defs.setdefault(m[1],[]).append((i,l.strip()))
need=set(targets); seen=set(); out=[]
while need:
    v=need.pop()
    if v in seen: continue
    seen.add(v)
    for i,l in defs.get(v,[]):
        out.append((i,l))
        for w in re.findall(r'_\d+|in\.\w+|spvDescriptorSet0\.\w+',l.split('=',1)[1]): need.add(w)
for i,l in sorted(set(out)): print(f'{lo+i}: {l}')
