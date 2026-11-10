import re,sys
def parse(path,lo,hi):
    lines=open(path).read().split('\n')[lo-1:hi]
    defs={}; stores=[]
    for l in lines:
        l=l.strip()
        m=re.match(r'(%[\w.]+) = (.*)',l)
        if m: defs[m[1]]=m[2]
        m=re.match(r'store float (%[\w.]+), float addrspace\(3\)\*',l)
        if m: stores.append(m[1])
    return defs,stores
def operands(d):
    # operands after the type keyword(s)
    return re.findall(r'(?:float|i32|i1|i8|i64) (%[\w.]+|-?[\d.e+-]+|0x[0-9A-Fa-f]+|true|false)',d)
def tree(defs,v,depth=0):
    if not v.startswith('%'): return 'c'+v
    if depth>80: return 'DEEP'
    d=defs.get(v)
    if d is None: return 'ARG'
    op=d.split(' ',1)[0]
    if op=='load':
        sp=re.search(r'addrspace\((\d)\)',d); t=d.split(' ')[1].rstrip(',')
        return f'load:{t}:as{sp[1] if sp else 0}'
    if op in ('fmul','fadd','fsub','fdiv','fneg','fcmp'):
        flags=[w for w in d.split(' ')[1:4] if w in ('fast','nnan','ninf','nsz','arcp','contract','afn','reassoc')]
        m=re.search(r'float (.*)$',d); ops=[o.strip() for o in m[1].split(',')] if m else []
        return f'{op}{"["+" ".join(flags)+"]" if flags else ""}(' + ','.join(tree(defs,o,depth+1) for o in ops) + ')'
    if op=='call':
        name=re.search(r'@([\w.]+)',d)[1]; ops=operands(d.split('(',1)[1])
        return f'{name}(' + ','.join(tree(defs,o,depth+1) for o in ops) + ')'
    if op=='select':
        ops=re.findall(r'(%[\w.]+|-?[\d.e+-]+|0x[0-9A-Fa-f]+|true|false)',d)
        return 'select(' + ','.join(tree(defs,o,depth+1) for o in ops[1:4]) + ')'
    if op in ('bitcast','fptrunc','fpext','sitofp','uitofp','fptosi','fptoui','extractelement'):
        return f'{op}(' + ','.join(tree(defs,o,depth+1) for o in re.findall(r'(%[\w.]+)',d)) + ')'
    if op=='phi': return 'PHI'
    return 'INT'
path,lo,hi=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
defs,stores=parse(path,lo,hi)
for s in stores: print(tree(defs,s)); print()
