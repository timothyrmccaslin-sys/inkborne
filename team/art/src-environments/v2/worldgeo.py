import json,numpy as np
J=json.load(open('/workspace/inkborne/data/world.json'))
S=2.0
N={n['id']:(n['x']*S,n['y']*S) for n in J['nodes']}
def curves(steps=200):
    out=[]
    for e in J['paths']:
        a,b=e[0],e[1]; c=e[2] if len(e)>2 else []
        P=[np.array(N[a])]+[np.array((x*S,y*S)) for x,y in c]+[np.array(N[b])]
        t=np.linspace(0,1,steps)[:,None]
        if len(P)==4: p=((1-t)**3)*P[0]+3*((1-t)**2)*t*P[1]+3*(1-t)*t*t*P[2]+t**3*P[3]
        elif len(P)==3: p=((1-t)**2)*P[0]+2*(1-t)*t*P[1]+t*t*P[2]
        else: p=P[0]*(1-t)+P[-1]*t
        out.append(p)
    return out
