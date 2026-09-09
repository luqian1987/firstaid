# -*- coding: utf-8 -*-
import openpyxl, json, collections
SRC="/root/.claude/uploads/12e5ca2d-7231-5774-9600-1c84384c6276/f37a786e-_____________________.xlsx"
DIM={  # 设备名称 -> (W,D,H) cm  来自 PPT《设备尺寸参数》
 "超净工作台":(150,75,160),"纯水仪":(93,51,90),"冷藏冷冻箱":(40,46,69),
 "生物安全柜（A2型）":(150,80,205),"PCR扩增仪":(43,29,23),"高速离心机":(38,50,36),
 "掌式离心机":(18,16,12),"漩涡振荡器":(13,16,15),"恒温混匀仪":(30,22,18),
 "垂直混匀仪":(40,15,20),"全自动毛细管电泳仪":(24,21,30),"荧光定量仪":(14,25,6),
 "MGISEQ-2000 基因组测序仪":(109,76,71),"分析解读一体机":(103,58,41),
}
FLOOR={"纯水仪","冷藏冷冻箱","生物安全柜（A2型）","MGISEQ-2000 基因组测序仪","分析解读一体机","抽湿机"}
SMALL_W={"单道移液器":8,"八道移液器":9,"磁力架":10,"96孔磁力架（八排管）":12,"计时器":8,"温湿度计":6}

wb=openpyxl.load_workbook(SRC,data_only=True); ws=wb.active
rooms=collections.OrderedDict(); room=zone=None
for r in ws.iter_rows(min_row=2,values_only=True):
    a,b,c,d,e,f,g,h=(list(r)+[None]*8)[:8]
    if c=="产品编码": continue
    if a: room,zone=str(a).strip(),(str(b).strip() if b else "")
    if room and d:
        rooms.setdefault(room,{"zone":zone,"items":[]})["items"].append(
            {"code":str(c).strip(),"product":str(d).strip(),"dev":str(f).strip(),
             "spec":("" if g in (None,"—","-") else str(g).strip()),"qty":int(h or 1)})

out=[]
for rn,rd in rooms.items():
    bench=0.0; floor=[]; nb=0
    for it in rd["items"]:
        dv=it["dev"]
        if dv in FLOOR:
            w,dp = (DIM[dv][0],DIM[dv][1]) if dv in DIM else (60,60)
            floor.append((dv,w,dp,round(w*dp/10000,2)))
        elif dv in DIM:
            bench+=DIM[dv][0]; nb+=1
        else:
            bench+=SMALL_W.get(dv,10); nb+=1
    gaps=max(0,nb-1)*15
    run=bench+gaps
    out.append({"room":rn,"zone":rd["zone"],"kinds":len(rd["items"]),
                "qty":sum(i["qty"] for i in rd["items"]),
                "bench_cm":round(bench),"run_cm":round(run),"run_m":round(run/100+0.4,1),
                "floor":floor,"floor_m2":round(sum(f[3] for f in floor),2),
                "items":rd["items"]})
for o in out:
    print(f"{o['room']:8s} {o['zone']:10s} 品类{o['kinds']:3d} 台面器械净宽{o['bench_cm']:4d}cm 含间隙{o['run_cm']:4d}cm→建议台面≥{o['run_m']}m 落地{o['floor_m2']}㎡ {[f[0] for f in o['floor']]}")
json.dump(out,open("/tmp/claude-0/-home-user-firstaid/12e5ca2d-7231-5774-9600-1c84384c6276/scratchpad/rooms.json","w"),ensure_ascii=False,indent=1)
