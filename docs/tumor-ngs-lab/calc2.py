# -*- coding: utf-8 -*-
import json, math
rooms=json.load(open("rooms.json"))
DIM={"超净工作台":150,"PCR扩增仪":43,"高速离心机":38,"掌式离心机":18,"漩涡振荡器":13,
     "恒温混匀仪":30,"垂直混匀仪":40,"全自动毛细管电泳仪":24,"荧光定量仪":14,
     "磁力架":10,"96孔磁力架（八排管）":12}
IGNORE={"计时器","温湿度计"}                      # 壁挂/不占台面
FLOORSET={"纯水仪":(93,51),"冷藏冷冻箱":(40,46),"生物安全柜（A2型）":(150,80),
          "MGISEQ-2000 基因组测序仪":(109,76),"分析解读一体机":(103,58),"抽湿机":(50,40)}
res=[]
for o in rooms:
    bench=[]; floor=[]; single=multi=0
    for it in o["items"]:
        dv=it["dev"]
        if dv in IGNORE: continue
        if dv in FLOORSET: floor.append((dv,)+FLOORSET[dv]); continue
        if dv=="单道移液器": single+=1; continue
        if dv=="八道移液器": multi+=1; continue
        bench.append((dv,DIM.get(dv,20)))
    rack = (45 if single else 0)+(25 if multi else 0)
    if rack: bench.append(("移液器架（%d单道%s）"%(single,"+%d八道"%multi if multi else ""),rack))
    w=sum(b[1] for b in bench); gaps=max(0,len(bench)-1)*10
    run=w+gaps
    wall_extra=sum(f[1] for f in floor if f[0]=="生物安全柜（A2型）")
    room_len = run/100 + 0.5
    area = max(8, math.ceil(room_len*2.6))
    if o["room"]=="PCR8": area=12; room_len=0
    if wall_extra: area=max(area,12)
    res.append(dict(room=o["room"],zone=o["zone"],kinds=o["kinds"],
        bench_items=len(bench),bench_cm=w,run_cm=run,run_m=round(run/100,1),
        floor=[f"{f[0]} {f[1]}×{f[2]}cm" for f in floor],
        floor_m2=round(sum(f[1]*f[2]/10000 for f in floor),2), area=area))
tot=0
for r in res:
    tot+=r["area"]
    print(f"{r['room']:8s}{r['zone']:11s}品类{r['kinds']:3d} 台面{r['bench_items']:2d}件/净宽{r['bench_cm']:3d}cm→台面≥{r['run_m']}m  落地{r['floor_m2']:.2f}㎡ 建议≥{r['area']}㎡  {r['floor']}")
print("合计建议净使用面积 ≥", tot, "㎡（不含缓冲间）")
json.dump(res,open("area.json","w"),ensure_ascii=False,indent=1)
