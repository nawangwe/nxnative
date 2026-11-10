import re,sys,collections
def parse(path):
    body=open(path).read()
    # take the dm_stage_body function (first define containing 'dm_stage_body') else whole
    funcs=re.findall(r'(define [^\n]*?(\w*dm_stage_body\w*)[^\n]*\{\n.*?\n\})',body,re.S)
    text=funcs[0][0] if funcs else body
    defs={}; stores=[]
    for l in text.split('\n'):
        l=l.strip()
        m=re.match(r'(%[\w.]+) = (.*)',l)
        if m: defs[m[1]]=m[2]
        m=re.match(r'store i32 (%[\w.]+), (?:ptr|i32\*) addrspace\(3\)',l) or re.match(r'store i32 (%[\w.]+), i32 addrspace\(3\)\*',l)
        if m: stores.append(m[1])
    return defs,stores
FLOATOPS=('fmul','fadd','fsub','fneg','fdiv','select','phi','call float @llvm.fma','call float @air.fma','call float @air.fast_fma','call float @llvm.fmuladd','bitcast','fptrunc','fpext','sitofp','uitofp')
def tree(defs,v,depth=0):
    if depth>60: return 'DEEP'
    d=defs.get(v)
    if d is None: return 'ARG'
    op=d.split(' ',1)[0]
    if d.startswith('load'):
        m=re.search(r'addrspace\((\d)\)',d); sp=m[1] if m else '0'
        t=d.split(' ')[1]
        return f'load:{t}:as{sp}'
    if op in ('fmul','fadd','fsub','fdiv','fneg') or d.startswith('fcmp'):
        flags=' '.join(w for w in d.split(' ')[1:] if w in ('fast','nnan','ninf','nsz','arcp','contract','afn','reassoc'))
        ops=re.findall(r'(%[\w.]+|[-\d.e+]+|0x[0-9A-Fa-f]+)',d.split('float',1)[1]) if 'float' in d else []
        return f'{op}[{flags}](' + ','.join(tree(defs,o,depth+1) if o.startswith('%') else 'c'+o for o in ops) + ')'
    if d.startswith('call'):
        name=re.search(r'@([\w.]+)',d)[1]
        args=re.findall(r'(?:float|i32|i1) (%[\w.]+|[-\d.e+]+|0x[0-9A-Fa-f]+|true|false)',d.split('(',1)[1]) if '(' in d else []
        return f'{name}(' + ','.join(tree(defs,o,depth+1) if o.startswith('%') else 'c'+o for o in args) + ')'
    if op in ('select',):
        ops=re.findall(r'(%[\w.]+|[-\d.e+]+|0x[0-9A-Fa-f]+|true|false)',d)
        return 'select(' + ','.join(tree(defs,o,depth+1) if o.startswith('%') else 'c'+o for o in ops[:3]) + ')'
    if op in ('bitcast','fptrunc','fpext','sitofp','uitofp','trunc','zext','sext','and','or','xor','shl','lshr','ashr','add','sub','mul','icmp','extractelement','insertelement','shufflevector','getelementptr','phi'):
        ops=re.findall(r'(%[\w.]+)',d)
        if op in ('bitcast','fptrunc','fpext'): return f'{op}(' + ','.join(tree(defs,o,depth+1) for o in ops) + ')'
        return 'INT'   # integer / address math: opaque
    return op
for path in sys.argv[1:]:
    defs,stores=parse(path)
    trees=[tree(defs,s) for s in stores]
    print('==',path,len(stores),'shared stores')
    for t in trees: print('  ',t[:400])
