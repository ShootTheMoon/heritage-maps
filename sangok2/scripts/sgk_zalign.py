# -*- coding: utf-8 -*-
"""sgk_zalign.py — 배치 z 재정렬: 마스터 메시의 바닥 정점(뿌리·밑동)을 실제로 월드에 놓고 지면 위로 나오는 정점이 0이 되게 인스턴스별 z 를 내린다.
   blender.exe -b 00_Source_Blender\SGK_Master.blend --python _scripts\sgk_zalign.py   (placements_master.json 갱신 + 마스터 동기화 저장)"""
import bpy, sys, os, json, math
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE); import sgk_layout as L
P=os.path.join(os.path.dirname(HERE),"05_Documentation","placements_master.json")
pm=json.load(open(P,encoding="utf-8"))
SKIP={"MST_PAVILION","MST_BRIDGE","MST_WALL_9M","MST_WALL_L"}
BASE={}
for m in sorted({i["master"] for i in pm["instances"]}):
    ob=bpy.data.objects.get(m)
    if not ob or m in SKIP: continue
    me=ob.data
    if any(k in m for k in ("PINE_M","PINE_L","PINE_XL")):      # 큰 소나무: 뿌리 띠 (줄기 반경 밖, z<1.2)
        tr=max((math.hypot(v.co.x,v.co.y) for v in me.vertices if 2.5<v.co.z<3.5), default=0.3)
        pts=[(v.co.x,v.co.y,v.co.z) for v in me.vertices if v.co.z<1.2 and math.hypot(v.co.x,v.co.y)>tr*1.15]
    else:                                                          # 묘목·작은 소나무·프롭·바위: 밑동 링만 (가지를 뿌리로 오인하지 않게)
        pts=[(v.co.x,v.co.y,v.co.z) for v in me.vertices if v.co.z<0.25]
    step=max(1,len(pts)//800); BASE[m]=pts[::step]; print(m,"base",len(pts),"->",len(BASE[m]))
FOOT={"MST_PINE_XL2":(1.5,1.0),"MST_PINE_L2":(1.4,1.0),"MST_PINE_XL":(1.5,0.7),"MST_PINE_L":(0.9,0.7),"MST_PINE_M":(1.0,0.7),"MST_PINE_S":(0.7,0.35),"MST_SAPLING":(0.6,0.12),"MST_STUMP":(0.9,0.12),"MST_DEADTRUNK":(1.5,0.08),"MST_FERN":(0.9,0.08),"MST_EULALIA":(0.4,0.05),"MST_ARTEMISIA":(0.4,0.05),"MST_BOULDER":(0.6,0.25),"MST_ROCK":(0.6,0.25)}
for it in pm["instances"]:
    f=next((v for k,v in FOOT.items() if it["master"].startswith(k)), None)
    if not f: continue
    r=f[0]*it.get("scale",1.0); x,y=it["x"],it["y"]
    ptsg=[(x+r*math.cos(a), y+r*math.sin(a)) for a in [i*math.pi/4 for i in range(8)]]+[(x,y)]
    it["z"]=round(min(L.height_at(px,py) for px,py in ptsg)-f[1],3)
changed=0; worst=[]
for it in pm["instances"]:
    pts=BASE.get(it["master"])
    if not pts: continue
    s=it.get("scale",1.0); a=math.radians(it["yaw"]); ca,sa=math.cos(a),math.sin(a); need=0.0
    for x,y,z in pts:
        wx=it["x"]+(x*ca-y*sa)*s; wy=it["y"]+(x*sa+y*ca)*s; wz=it["z"]+z*s
        need=max(need, wz-(L.height_at(wx,wy)-0.03))
    if "ROCK" in it["master"] or "BOULDER" in it["master"]:        # 바위는 높이의 35 % 까지만 (절벽 가장자리 바위가 통째로 사라지지 않게)
        need=min(need, 0.35*it["dims"][2])
    if need>0.005: it["z"]=round(it["z"]-need,3); changed+=1; worst.append((round(need,2),it["name"],it["master"]))
worst.sort(reverse=True); print("changed",changed,"worst",worst[:10])
json.dump(pm,open(P,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
for it in pm["instances"]:
    o=bpy.data.objects.get(it["name"])
    if o: o.location=(it["x"],it["y"],it["z"]); o.rotation_euler=(0,0,math.radians(it["yaw"]))
bpy.ops.wm.save_mainfile(); print("SAVED", len(bpy.data.objects), sum(1 for i in bpy.data.images if i.packed_file))
