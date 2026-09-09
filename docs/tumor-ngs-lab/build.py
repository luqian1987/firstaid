# -*- coding: utf-8 -*-
import openpyxl, json, html, collections, re
UP="/root/.claude/uploads/12e5ca2d-7231-5774-9600-1c84384c6276/"
area={a["room"]:a for a in json.load(open("area.json"))}
E=html.escape

META=[
 dict(room="试剂准备间",zone="试剂准备区",z=1,no="R1",
  desc="配制与分装 PCR 反应体系、储存试剂。全区洁净度最高，维持相对正压；人员当日进入本间后，不再进入下游任一功能间。",
  keys=["超净工作台 ACB-1300V 双人垂直单流","纯水仪 18.2 MΩ","冷藏冷冻箱 2–8 ℃ & −20 ℃"],
  need="需<b>上下水点位</b>——纯水仪进水与排水；独立空调与正压送风。超净工作台 150×75 cm 建议独占一面墙。"),
 dict(room="PCR2",zone="标本与文库制备区",z=2,no="R2",
  desc="组织 / 石蜡样本的核酸提取与文库构建。配 A2 型生物安全柜操作开放性生物样本，是全流程中生物安全等级最高的一间。",
  keys=["生物安全柜 A2 型 1500×815×2270","PCR 扩增仪 ETC-821M","高速离心机 1.5 mL 转子","恒温混匀仪 96 孔 + 1.5 模块","磁力架 16 孔 + 96 孔"],
  need="生物安全柜整机高 <b>205 cm</b>，需确认吊顶净高与排风路由，柜前应留 ≥1.0 m 操作空间。<b>清单未含自动化核酸提取仪</b>，落位待定。"),
 dict(room="PCR3",zone="血浆文库制备区",z=3,no="R3",
  desc="血浆游离 DNA（cfDNA）文库构建。与组织样本物理分离，避免高浓度组织 DNA 污染低丰度 ctDNA 检测——这是单设一间的核心理由。",
  keys=["生物安全柜 A2 型","PCR 扩增仪","高速离心机","恒温混匀仪","磁力架 16 孔 + 96 孔"],
  need="设备配置与 PCR2 完全一致。<b>血浆分离所需的高速冷冻离心机、以及血浆与文库的 −80 ℃ 存储条件</b>需另行确认。"),
 dict(room="PCR4",zone="杂交捕获区",z=4,no="R4",
  desc="探针杂交、磁珠捕获与洗脱。设备品类最多的一间（21 项），也是台面需求最长的一间，但无落地大型设备。",
  keys=["垂直混匀仪 HS-3","恒温混匀仪","PCR 扩增仪","荧光定量仪 Fluo-200","96 孔磁力架","高速离心机"],
  need="台面净长需求最大，<b>建议沿两面墙 L 形布置</b>；本间面积主要由台面长度而非设备占地决定。"),
 dict(room="PCR5",zone="文库扩增与检测区",z=5,no="R5",
  desc="捕获后文库扩增与上机前质检（浓度与片段分布）。扩增产物在此首次大量出现，是污染风险的分水岭。",
  keys=["全自动毛细管电泳仪 Qsep1","荧光定量仪 Fluo-200","PCR 扩增仪"],
  need="自本间起为<b>扩增产物高负载区，须维持相对负压</b>，人员与物品不得逆向返回上游任一功能间。"),
 dict(room="PCR8",zone="测序区",z=6,no="R6",
  desc="MGISEQ-2000 上机测序与生信分析解读。全流程终点，设备数量最少，但对环境控制、供电稳定性与数据链路的要求最高。",
  keys=["MGISEQ-2000 基因测序仪 1086×756×710","Halos 分析解读一体机","抽湿机 OJ-501E"],
  need="需<b>独立空调控温与湿度控制</b>（已配抽湿机）；<b>UPS 与电池柜未列入清单，须补配</b>——测序中断电将报废整个 run；楼面承重与院内网接入待确认。"),
]

# ---------- STRIP ----------
strip=[]
for m in META:
    a=area[m["room"]]
    strip.append(f'''<div class="room" style="--zc:var(--z{m['z']})">
  <div class="buf">缓冲间</div>
  <div class="rbody">
    <div class="rno">{m['no']}　{E(m['room'])}</div>
    <div class="rname">{E(m['zone'])}</div>
    <div class="rzone">设备 {a['kinds']} 项</div>
    <div class="rstat"><span>台面 {'<b>≥'+str(a['run_m'])+'</b>m' if a['run_m']>0 else '<b>—</b>'}</span><span>面积 <b>≥{a['area']}</b>㎡</span></div>
  </div></div>''')

# ---------- CARDS ----------
cards=[]
for m in META:
    a=area[m["room"]]
    chips="".join(f'<span class="chip hi">{E(k)}</span>' if i==0 else f'<span class="chip">{E(k)}</span>'
                  for i,k in enumerate(m["keys"]))
    bench=f'≥ {a["run_m"]} m（台面器械 {a["bench_items"]} 件，净宽合计 {a["bench_cm"]} cm）' if a["run_m"]>0 else '无台面器械需求（设备均落地）'
    floor=("、".join(a["floor"]) if a["floor"] else "无") + (f'　占地 {a["floor_m2"]} ㎡' if a["floor"] else "")
    cards.append(f'''<article class="card" style="--zc:var(--z{m['z']}); --zs:var(--z{m['z']}s)">
  <div class="chead"><span class="cno">{m['no']}</span><h3>{E(m['zone'])}</h3><span class="cz mono">{E(m['room'])}</span></div>
  <div class="cbody">
    <p>{m['desc']}</p>
    <div class="keylist">{chips}</div>
    <dl class="kv">
      <dt>设 备</dt><dd>{a['kinds']} 项 / {a['kinds']} 台件</dd>
      <dt>建议台面</dt><dd>{bench}</dd>
      <dt>落地设备</dt><dd>{E(floor)}</dd>
      <dt>建议面积</dt><dd><b class="mono">≥ {a['area']} ㎡</b> 净使用面积（含 0.75 m 台面进深与 ≥1.2 m 通行净宽）</dd>
    </dl>
    <div class="need"><b>配套要求　</b>{m['need']}</div>
  </div></article>''')

# ---------- EQUIP TABLE ----------
wb=openpyxl.load_workbook(UP+"f37a786e-_____________________.xlsx",data_only=True); ws=wb.active
rooms=collections.OrderedDict(); room=zone=None
for r in ws.iter_rows(min_row=2,values_only=True):
    a_,b,c,d,e,f,g,h=(list(r)+[None]*8)[:8]
    if c=="产品编码": continue
    if a_: room,zone=str(a_).strip(),(str(b).strip() if b else "")
    if room and d:
        rooms.setdefault(room,[]).append(dict(code=str(c).strip(),prod=str(d).strip(),
            dev=str(f).strip(),spec=("—" if g in (None,"—","-") else str(g).strip()),qty=int(h or 1)))
zmap={m["room"]:m["z"] for m in META}
rows=[]
for rn,items in rooms.items():
    z=zmap[rn]; zone=[m["zone"] for m in META if m["room"]==rn][0]
    n=sum(i["qty"] for i in items)
    rows.append(f'<tbody class="grp"><tr class="grp" style="--zc:var(--z{z}); --zs:var(--z{z}s)">'
                f'<th colspan="5">{E(rn)} · {E(zone)}<span class="mono">{len(items)} 项 / {n} 台件</span></th></tr></tbody>')
    body=[]
    single=[i for i in items if i["dev"]=="单道移液器"]
    multi=[i for i in items if i["dev"]=="八道移液器"]
    for it in items:
        if it["dev"] in ("单道移液器","八道移液器"): continue
        body.append(f'<tr><td class="code">{E(it["code"])}</td><td>{E(it["prod"])}</td>'
                    f'<td>{E(it["dev"])}</td><td>{E(it["spec"])}</td><td class="num">{it["qty"]}</td></tr>')
    for grp,label in ((single,"单道移液器"),(multi,"八道移液器")):
        if not grp: continue
        rng=[re.sub(r'^.*?移液器','',x["prod"]).strip() for x in grp]
        codes=" / ".join(x["code"] for x in grp)
        body.append(f'<tr><td class="code">{E(codes)}</td>'
                    f'<td>TIANGEN {E(label)}　<span class="mono" style="font-size:12px;color:var(--muted)">{E(" · ".join(rng))}</span></td>'
                    f'<td>{E(label)}</td><td>—</td><td class="num">{len(grp)}</td></tr>')
    rows.append("<tbody>"+"".join(body)+"</tbody>")

# ---------- KITS ----------
wb2=openpyxl.load_workbook(UP+"165b8495-___________.xlsx",data_only=True); ws2=wb2.active
kr=[]
for r in ws2.iter_rows(min_row=2,values_only=True):
    no,name,mfr,reg,scope,ext,bar,price=(list(r)+[None]*8)[:8]
    if not no: continue
    ext=(str(ext).strip() if ext else "") or "—"
    kr.append(f'''<tr>
      <td class="num" style="text-align:left">{E(str(no))}</td>
      <td class="w"><b>{E(str(name).strip())}</b><br><span style="font-size:12px;color:var(--muted)">{E(str(mfr).strip())}</span></td>
      <td class="code">{E(str(reg).strip())}</td>
      <td style="min-width:6em">{E(str(scope).strip())}</td>
      <td class="w" style="font-size:12.5px;color:var(--ink-2)">{E(ext)}</td>
      <td class="num"><b>{int(price):,}</b> 元</td></tr>''')
kits=('<thead><tr><th>#</th><th>试剂盒 / 生产厂家</th><th>注册证号</th><th>注册适用范围</th>'
      '<th>可拓展适用范围</th><th style="text-align:right">物价收费</th></tr></thead><tbody>'
      +"".join(kr)+'</tbody>')

tpl=open("tpl.html",encoding="utf-8").read()
tpl=tpl.replace("__STRIP__","\n".join(strip)).replace("__CARDS__","\n".join(cards))
tpl=tpl.replace("__EQUIP__","\n".join(rows)).replace("__KITS__",kits)
assert "__" not in tpl.replace("__","",0) or True
for tok in ("__STRIP__","__CARDS__","__EQUIP__","__KITS__"):
    assert tok not in tpl, tok
open("ngs-lab.html","w",encoding="utf-8").write(tpl)
print("written", len(tpl), "bytes")
