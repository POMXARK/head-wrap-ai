"""Test of the lama arm of head_tools.py (corsairs-remake): a dark patch is filled, nothing outside changes, the arm is in head_agent.ARMS."""
import sys, numpy as np, types
import os; sys.path.insert(0, os.path.join(os.environ.get('W','/media/roman/383be9ee-c114-4bf8-8956-66b985661cb4/home/remake-linux'), 'corsairs-remake/tools/model3d'))
import head_tools as ht
rng=np.random.default_rng(0)
img=(rng.random((256,256,3))*10+120).astype(np.float32); img[100:130,100:130]=20  # dark patch
h=types.SimpleNamespace(img=img.copy())
m=np.zeros((256,256),bool); m[98:132,98:132]=True
ht.texels=lambda h,mask: m
note=ht.lama(h,None,grow=1,context=60)
print(note)
print('patch mean before', img[100:130,100:130].mean(), 'after', h.img[100:130,100:130].mean(), 'outside changed', bool((h.img[:90]!=img[:90]).any()))
assert abs(h.img[100:130,100:130].mean()-125)<15 and not (h.img[:90]!=img[:90]).any()
print('PASS')
import head_agent as ha; assert ('lama',{'grow':1}) in ha.ARMS and 'lama' in ht.TOOLS; print('arms ok', ha.arm_id(('lama',{'grow':3})))
