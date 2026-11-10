#!/usr/bin/env python3
"""For each foliage pair (depth-prepass mesh shader, colour mesh shader): every value the prepass body stores to its output memory must be computed identically
in the colour body (positions above all). Signatures are the structural expression trees with SSA names erased and uniform / texture names replaced by NVN registers."""
import re, sys, json, sqlite3, hashlib, resource
try: resource.setrlimit(resource.RLIMIT_AS, (3<<30, resource.RLIM_INFINITY))
except ValueError: pass
sys.setrecursionlimit(100000)
DB='/Users/maximnawangwe/Games/OcarinaOfTime/penis6_build/shader/cache/cas.db'
c=sqlite3.connect(f'file:{DB}?mode=ro&immutable=1',uri=True)
def regs(key):
    j=json.loads(c.execute("select b.data from entry e join blob b on b.id=e.blob where e.name like ? order by e.mtime desc limit 1",(f'%/mac/{key}_b.json',)).fetchone()[0])
    m={}
    for b in j['bindings']:
        if b.get('kind') in ('cbuf','tex','sbuf'): m[b['msl_name']]=f"{b['kind']}{b.get('reg')}"
        elif b.get('kind')=='c1': m[b['msl_name']]='c1'
        elif b.get('kind')=='drvcb': m[b['msl_name']]='drv'
    return m
def load(key):
    src=open(f'sh/{key}_b.metal').read(); rm=regs(key)
    body=src[src.find('dm_stage_body'):]
    assign={m[1]:m[2] for m in re.finditer(r'\n\s+(?:float|int|uint|bool|float[234]|half|uint[234]|int[234])\s+(_\d+)\s*=\s*([^;]+);',body)}
    arr=re.search(r'threadgroup spvUnsafeArray<uint, \d+> (_\d+);',src)[1]
    stores=[(m[1],m[2]) for m in re.finditer(r'\n\s+'+arr+r'\[int\((_\d+)\)\] = (?:as_type<uint>\()?(_\d+|\d+u)\)?;',body)]
    memo={}
    def sig(v,d=0):
        if v in memo: return memo[v]
        if v not in assign: return v
        e=assign[v]
        e=re.sub(r'\(\*spvDescriptorSet0\.(\w+)\)',lambda m: rm.get(m[1],m[1]),e); e=re.sub(r'spvDescriptorSet0\.(\w+)',lambda m: rm.get(m[1],m[1]),e)
        e=re.sub(r'\b'+arr+r'\[',' SM[',e)
        if d>2000: return 'deep'
        s=hashlib.sha1(re.sub(r'_\d+',lambda m: '('+sig(m[0],d+1)+')',e).encode()).hexdigest()[:16]   # a hash of the template with the children's hashes: bounded size
        memo[v]=s; return s
    return stores,sig
pairs=[('839241636fce850a','4c7d6be5a7717c8d'),('a934ed1af79131cc','edeefae4c37b0257'),('a667b8bba94befa2','3fa631a86435d3e8'),('d98076e4148db34f','fed302d791a4ba43'),
       ('eebdb9347d09b344','604134a5262ff670'),('5b737961ae3e1b10','ecead5cd0569091f'),('65a079a285d693a0','eb021183bf9b0092')]
for pre,col in pairs:
    ps,psig=load(pre); cs,csig=load(col)
    pre_vals=[(v,psig(v)) for i,v in ps if v.startswith('_')]; col_sigs={csig(v) for i,v in cs if v.startswith('_')}
    missing=[(v,s) for v,s in pre_vals if s not in col_sigs]
    print(f'{pre[:8]} -> {col[:8]}: prepass stores {len(ps)} (values {len(pre_vals)}), colour stores {len(cs)}; prepass values with NO identical computation in the colour shader: {len(missing)}')
    for v,s in missing[:6]: print('    ',v,'=',psig.__globals__.get('_',''),re.sub(r'\s+',' ',open(f'sh/{pre}_b.metal').read().split(f' {v} = ')[1].split(';')[0])[:160] if f' {v} = ' in open(f'sh/{pre}_b.metal').read() else '')
