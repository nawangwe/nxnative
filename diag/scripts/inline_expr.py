import re,sys
path,lo,hi=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]); targets=sys.argv[4:]
lines=open(path).read().split('\n')[lo-1:hi]
defs={}
for l in lines:
    m=re.match(r'\s*(?:float\d?|int|uint|bool|half\d?)?\s*(_\d+)\s*=\s*(.*);$',l.strip())
    if m and m[1] not in defs: defs[m[1]]=m[2]
memo={}
def expand(v,depth=0):
    if v in memo: return memo[v]
    e=defs.get(v)
    if e is None: return v
    def rep(m):
        w=m[0]
        return '('+expand(w,depth+1)+')' if w in defs else w
    r=re.sub(r'_\d+',rep,e)
    r=r.replace('(*spvDescriptorSet0.','(').replace('as_type<float>(in.m_27','IDX(in.m_27')
    memo[v]=r; return r
for t in targets:
    s=expand(t); print(t, len(s)); print(s[:1200]); print()
