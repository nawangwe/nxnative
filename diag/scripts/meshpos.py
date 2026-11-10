import re,sys
def load(path, arr):
    src=open(path).read().split('\n')
    lo=next(i for i,l in enumerate(src) if 'void dm_stage_body(' in l); hi=next(i for i,l in enumerate(src) if i>lo and l.startswith('struct dm_payload_t'))
    body=src[lo:hi]; d={}; stores=[]
    for l in body:
        s=l.strip()
        m=re.match(r'(?:float\d?|int|uint|bool|half\d?)?\s*(_\d+)\s*=\s*(.*);$',s)
        if m and m[1] not in d: d[m[1]]=m[2]
        m=re.match(r'%s\[int\((_\d+)\)\] = as_type<uint>\((_\d+)\);$'%arr,s)
        if m: stores.append((m[1],m[2]))
    memo={}
    def ex(v,depth=0):
        if v in memo: return memo[v]
        e=d.get(v)
        if e is None: return v
        r=re.sub(r'_\d+',lambda m:'('+ex(m[0])+')' if m[0] in d else m[0],e)
        r=r.replace('(*spvDescriptorSet0.','(')
        memo[v]=r; return r
    return [(ex(i),ex(v)) for i,v in stores]
P=load('e8c667282ba7bd9b_b.metal','_33'); C=load('35785cddc971290c_b.metal','_37')
print('prepass stores',len(P),' colour stores',len(C))
cvals={v:i for i,v in C}
hit=miss=0
for i,v in P:
    if v in cvals: hit+=1
    else:
        miss+=1
        # closest colour value by common prefix
        best=max(C,key=lambda c: len(__import__('os').path.commonprefix([c[1],v])))
        k=len(__import__('os').path.commonprefix([best[1],v]))
        print(f'MISS idx={i[:60]}... len {len(v)}; closest colour expr diverges at {k} of {len(best[1])}:')
        print('   pre:',v[max(0,k-120):k+120]); print('   col:',best[1][max(0,k-120):k+120])
print('identical value expressions:',hit,'differing:',miss)
