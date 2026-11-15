import sys
import os
P=os.environ.get('RUSTY_WORK','/tmp/rusty-ib-work')+'/core/src/lib.rs'
def edits(pairs, path=P):
    s=open(path).read()
    for old,new in pairs:
        n=s.count(old)
        if n!=1: sys.exit(f"anchor count {n}: {old[:80]!r}")
        s=s.replace(old,new)
    open(path,'w').write(s)
