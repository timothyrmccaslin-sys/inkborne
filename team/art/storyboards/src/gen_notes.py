from zones import *
def row(c,n,x,y,w,h,note):
    pc=lambda v,t: f"{100*v/t:.1f}"
    if x==0 and y==0: return f"| {c} | {n} | floats, {w}×{h} | floats, {pc(w,1280)}%×{pc(h,720)}% | {note} |"
    return f"| {c} | {n} | {x}, {y}, {w}×{h} | {pc(x,1280)}%, {pc(y,720)}%, {pc(w,1280)}%×{pc(h,720)}% | {note} |"
HDR="| Code | Element | px (x, y, w×h) | % of 1280×720 (x, y, w×h) | Notes |\n|---|---|---|---|---|"
def table(rows): return HDR+"\n"+"\n".join(row(*r) for r in rows)
out=open("/tmp/LAYOUT_NOTES.md.tables","w")
out.write("RESERVED\n"+table(RESERVED)+"\n")
for k in ["world","poi","dialogue","shop","battle"]: out.write(k.upper()+"\n"+table(Z[k])+"\n")
