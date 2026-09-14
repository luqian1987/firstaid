# -*- coding: utf-8 -*-
"""郭 9.13 设备清单 vs szwzf 9.12：逐行归类，输出带标注的数据"""
import json, collections
from dumprev import rows, norm
U="/root/.claude/uploads/12e5ca2d-7231-5774-9600-1c84384c6276/"
G=[r for r in norm(rows(U+"d0c5c1ed-____-_____2026.9.13.docx","final"))]
S=[r for r in norm(rows(U+"04ea3553-____.docx","final"))]

def group(rs):
    g=collections.OrderedDict()
    for r in rs:
        room,step,dev,ven,mod,qty,use = r[:7]
        if not dev.strip(): continue          # 跳过空行
        g.setdefault((room,step),[]).append([dev,ven,mod,qty,use])
    return g
GG, SS = group(G), group(S)

# 房间对应：按 PCR 编号对齐（试剂准备间单列）
def pcr(room):
    import re
    m=re.match(r"PCR(\d+)", room); return int(m.group(1)) if m else 0
Sby={pcr(k[0]):(k,v) for k,v in SS.items()}
Gby={pcr(k[0]):(k,v) for k,v in GG.items()}

# 全局设备位置表，用于识别「移入 / 移出」
def where(gr):
    w=collections.defaultdict(set)
    for (room,_),items in gr.items():
        for d,*_ in items: w[d].add(pcr(room))
    return w
WS, WG = where(SS), where(GG)

def totals(gr):
    q=collections.Counter()
    for items in gr.values():
        for d,ven,mod,qty,use in items: q[d]+=int(qty or 0)
    return q
TS, TG = totals(SS), totals(GG)
# 9.12 版里每台设备的厂商／型号，用作待补项的建议值
REF={}
for items in SS.values():
    for d,ven,mod,qty,use in items: REF.setdefault(d,(ven,mod))

out=[]; notes=[]
for n,(gk,gitems) in sorted(Gby.items()):
    groom, gstep = gk
    sk = Sby.get(n)
    sroom, sstep, sitems = (sk[0][0], sk[0][1], sk[1]) if sk else (None,None,[])
    sidx = {d:i for i,(d,*_) in enumerate(sitems)}
    hdr = {"room":groom, "step":gstep,
           "room_old":sroom, "step_old":sstep,
           "room_changed": bool(sroom) and sroom!=groom,
           "step_changed": bool(sstep) and sstep!=gstep,
           "room_new": sroom is None}
    rws=[]
    for d,ven,mod,qty,use in gitems:
        if sroom is None:
            tag = "调入" if (d in TS and TS[d]==TG[d]) else "新增"
        elif d not in sidx:
            # 只有全院总台件数未变，才是真正换了房间；否则是增配
            tag = "调入" if (d in TS and TS[d]==TG[d]) else "新增"
        else:
            od=sitems[sidx[d]]
            diff=[]
            if od[1]!=ven: diff.append(("厂商",od[1],ven))
            if od[2]!=mod: diff.append(("型号",od[2],mod))
            if od[3]!=qty: diff.append(("数量",od[3],qty))
            if od[4]!=use: diff.append(("用途",od[4],use))
            tag="修改" if diff else "未变"
        row={"dev":d,"ven":ven,"mod":mod,"qty":qty,"use":use,"tag":tag}
        if tag=="修改": row["diff"]=diff
        if tag in ("新增","调入"): row["gtot"]=[TS.get(d,0), TG.get(d,0)]
        if not ven.strip() and not mod.strip():
            row["todo"]=True
            if d in REF: row["ref"]=list(REF[d])
        rws.append(row)
    # 本房间在 szwzf 有、郭已没有的设备
    # 通用器具几乎每间都有，逐间报「移出」只是噪音；只报专用仪器的真实迁移
    GENERIC={"单道移液器","八道移液器","计时器","温湿度计","漩涡振荡器","掌式离心机",
             "磁力架","96孔磁力架（八排管）","PCR扩增仪","恒温混匀仪","生物安全柜（A2型）",
             "高速离心机","荧光计"}
    gone=[d for d,*_ in sitems if d not in {r["dev"] for r in rws} and d not in GENERIC]
    if gone: hdr["gone"]=[{"dev":d,"moved_to":sorted(WG.get(d,set())-{n})} for d in gone]
    out.append({"hdr":hdr,"rows":rws})

# szwzf 有、郭已整间取消的房间
for n,(sk,sitems) in sorted(Sby.items()):
    if n not in Gby: notes.append(f"整间取消：{sk[0]}（{len(sitems)} 项）")

qty_moves=[{"dev":d,"old":TS.get(d,0),"new":TG.get(d,0),
            "sby":dict(sorted(((r,sum(1*int(i[3] or 0) for i in v if i[0]==d)) for r,v in
                      ((k[0],v) for k,v in SS.items())) )),
            "gby":dict(sorted(((r,sum(1*int(i[3] or 0) for i in v if i[0]==d)) for r,v in
                      ((k[0],v) for k,v in GG.items())) ))}
           for d in sorted(set(TS)|set(TG)) if TS.get(d,0)!=TG.get(d,0)]
todos=[{"room":g["hdr"]["room"], **{k:v for k,v in r.items() if k in ("dev","ref","qty","use")}}
       for g in out for r in g["rows"] if r.get("todo")]
json.dump({"groups":out,"notes":notes,"qty_moves":qty_moves,"todos":todos},
          open("equip_cmp.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
tot=sum(len(g["rows"]) for g in out)
cnt=collections.Counter(r["tag"] for g in out for r in g["rows"])
print("郭 9.13：",len(out),"个分区 ／",tot,"行 ／",
      sum(int(r["qty"] or 0) for g in out for r in g["rows"]),"台（件）")
print("szwzf 9.12：",len(SS),"个分区 ／",sum(len(v) for v in SS.values()),"行 ／",
      sum(int(i[3] or 0) for v in SS.values() for i in v),"台（件）")
print("归类：",dict(cnt))
for g in out:
    h=g["hdr"]; mk=[]
    if h["room_new"]: mk.append("★新增分区")
    if h["room_changed"]: mk.append(f'改名：{h["room_old"]} → {h["room"]}')
    if h["step_changed"]: mk.append(f'步骤：{h["step_old"]} → {h["step"]}')
    print(f'\n【{h["room"]}】{"；".join(mk) if mk else "分区名未变"}')
    for r in g["rows"]:
        if r["tag"]=="未变": continue
        d=("｜".join(f'{a}:{b or "空"}→{c or "空"}' for a,b,c in r.get("diff",[]))) if r["tag"]=="修改" else ""
        print(f'   [{r["tag"]}] {r["dev"]}  {d}{"  ⚠厂商型号未填" if r.get("todo") else ""}')
    for x in h.get("gone",[]):
        print(f'   [移出] {x["dev"]} → ' + (f'PCR{x["moved_to"]}' if x["moved_to"] else "已删除"))
for x in notes: print(x)
