"""Test of the speed-ups of head_auto (python3 tests/test_head_auto_speed.py): a try with the views aligned once for the head gives the same 12-view score (+-0.02) and Qwen guard (+-GUARD) as aligning in every try, and is faster. Needs glbcheck/ (hero1 data)."""
import sys, time, numpy as np
import os
W=os.environ.get('W','/media/roman/383be9ee-c114-4bf8-8956-66b985661cb4/home/remake-linux')
os.chdir(W+'/glbcheck')
sys.path.insert(0,W+'/corsairs-remake/tools/model3d')
import head_auto as A, head_tools as ht, head_views as hv
views={n:ht.pv.load_view(p) for n,p in zip(ht.pv.NAMES,['hero1_head_front.png','hero1_head_left.png','hero1_head_back.png','hero1_head_right.png'])}
h=ht.Head('fix2/afinal.glb',views,'parts20/parts.npy')
h.ref=hv.Reference('../corsairs-remake/pdm-game','hero1','ref12'); h.fit=hv.fit_frame(h.P,h.tris,h.ref); h.ref.adopt(h)
rep,faces=hv.evaluate(h,h.ref); dl=hv.defects(h,faces); kind,mask,size,names=dl[2]
t=time.time(); ht.ensure_aligned(h); print('T ensure_aligned',round(time.time()-t,1))
arm=('relax',{'steps':15})
def go(al):
    h2=h.copy(); h2.aligned=h.aligned if al else None
    t=time.time(); ht.apply(h2,'relax',mask,steps=15); ht.apply(h2,'repaint',ht.grow(h2,mask,1),views='all'); dt=time.time()-t
    return h2,dt
a,da=go(False); b,db=go(True)
tx=ht.texels(a,ht.grow(a,mask,1))
print('T repaint try old %.1fs new %.1fs'%(da,db))
print('T region texels',int(tx.sum()),'max colour diff',float(np.abs(a.img[tx]-b.img[tx]).max()),'mean',float(np.abs(a.img[tx]-b.img[tx]).mean()))
new_s,old_s=hv.evaluate(b,h.ref)[0]['score'],hv.evaluate(a,h.ref)[0]['score']
print('T score old',hv.evaluate(a,h.ref)[0]['score'],'new',hv.evaluate(b,h.ref)[0]['score'],'qwen guard old',A.guard_score(ht.region_score(a,mask)),'new',A.guard_score(ht.region_score(b,mask)))

go_=A.guard_score(ht.region_score(a,mask)); gn=A.guard_score(ht.region_score(b,mask))
assert abs(new_s-old_s)<=0.02, (new_s,old_s)
assert abs(gn-go_)<=A.GUARD, (gn,go_)
assert db<da, (db,da)
assert float(np.abs(a.img[tx]-b.img[tx]).mean())<5
print('PASS aligned-once repaint: same score, guard within GUARD, faster')
