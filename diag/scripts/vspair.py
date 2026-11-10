import re,sys,os,sqlite3
db=os.path.expanduser('~/Games/OcarinaOfTime/penis6_build/shader/cache/cas.db')
c=sqlite3.connect(f'file:{db}?mode=ro',uri=True)
def fetch(k):
    fn=f'{k}_b.metal'
    if os.path.exists(fn): return open(fn).read()
    r=c.execute("select e.name,b.data from entry e join blob b on b.id=e.blob where e.name like ? and e.name like '%_b.metal' order by e.mtime desc limit 1",(f'%{k}%',)).fetchone()
    if not r: return None
    d=r[1]
    if d[:4]==b'\x28\xb5\x2f\xfd':
        import zstandard; d=zstandard.ZstdDecompressor().decompressobj().decompress(d)
    open(fn,'wb').write(d); return d.decode(errors='replace')
def posexpr(src):
    lines=src.split('\n'); lo=next(i for i,l in enumerate(lines) if l.startswith('vertex main0_out main0(')); hi=next(i for i,l in enumerate(lines) if i>lo and l.startswith('vertex ')) if any(l.startswith('vertex ') for l in lines[lo+1:]) else len(lines)
    body=lines[lo:hi]; d={}; tgt={}
    for l in body:
        m=re.match(r'\s*(?:float\d?|int|uint|bool|half\d?)?\s*(_\d+)\s*=\s*(.*);$',l.strip())
        if m and m[1] not in d: d[m[1]]=m[2]
        m=re.match(r'\s*out\.gl_Position\.([xyzw]) = (.*);$',l)
        if m and m[2]!='0.0' and m[2]!='1.0' and not m[2].startswith('fma(out.gl_Position'): tgt[m[1]]=m[2]
    am={}
    for n,a in re.findall(r'(?:float4|uint4|int4|float\d?|uint\d?|int\d?) (m_\d+) \[\[attribute\((\d+)\)\]\]',src): am['in.'+n]='A'+a
    memo={}
    def ex(v):
        if v in memo: return memo[v]
        e=d.get(v)
        if e is None: return v
        r=re.sub(r'_\d+',lambda m:'('+ex(m[0])+')' if m[0] in d else m[0],e)
        r=r.replace('(*spvDescriptorSet0.','(').replace('spvDescriptorSet0.','')
        r=re.sub(r'in\.m_\d+',lambda m:am.get(m[0],m[0]),r)
        memo[v]=r; return r
    out={}
    for ch,e in tgt.items():
        r=re.sub(r'_\d+',lambda m:'('+ex(m[0])+')' if m[0] in d else m[0],e); r=re.sub(r'in\.m_\d+',lambda m:am.get(m[0],m[0]),r.replace('(*spvDescriptorSet0.','('))
        out[ch]=r
    return out
pairs=[l.split() for l in sys.stdin if l.strip()]
for pre,col,label in pairs:
    a=fetch(pre); b=fetch(col)
    if not a or not b: print(label,pre,col,'MISSING'); continue
    pa,pb=posexpr(a),posexpr(b)
    res=[]
    for ch in 'xyzw':
        x,y=pa.get(ch,''),pb.get(ch,'')
        if x==y: res.append(ch+':same')
        else:
            k=next((j for j in range(min(len(x),len(y))) if x[j]!=y[j]),min(len(x),len(y)))
            res.append(f'{ch}:DIFF@{k}/{len(x)}v{len(y)}')
    print(label,pre,col,' '.join(res))
