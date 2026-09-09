# -*- coding: utf-8 -*-
import openpyxl, html, collections, re
UP="/root/.claude/uploads/12e5ca2d-7231-5774-9600-1c84384c6276/"
E=html.escape

ROOMS=[
 dict(key="试剂准备间", badge="试剂准备间", zone="试剂准备区", z=1,
   what="配制与分装 PCR 反应体系，储存与分装试剂。全流程最洁净的一间，只出不进——试剂从这里发往下游，样本和文库永不进入本间。",
   cond="房间独立、带缓冲间，位于分区最上游，与所有含样本的房间物理隔开。",
   gear=[("超净工作台",1),("纯水仪",1),("冷藏冷冻箱",1),("漩涡振荡器",1),("掌式离心机",1),("单道移液器 ×6",6)]),
 dict(key="PCR2", badge="PCR2", zone="标本与文库制备区", z=2,
   what="石蜡切片、组织样本的核酸提取与文库构建。全流程唯一开放操作生物样本的环节，配 A2 型生物安全柜。",
   cond="独立成间、带缓冲，与试剂准备区完全分开，符合标本制备区的隔离要求。",
   gear=[("生物安全柜 A2 型",1),("PCR 扩增仪",1),("高速离心机",1),("恒温混匀仪",1),("磁力架 ×2",2)]),
 dict(key="PCR3", badge="PCR3", zone="血浆文库制备区", z=3,
   what="血浆游离 DNA（cfDNA）的文库构建。之所以单独一间，是因为组织样本的 DNA 浓度远高于血浆中的 ctDNA，同室操作会把低丰度突变淹掉。",
   cond="与 PCR2 相邻但完全分室，两间设备各自独立配置，不共用器具。",
   gear=[("生物安全柜 A2 型",1),("PCR 扩增仪",1),("高速离心机",1),("恒温混匀仪",1),("磁力架 ×2",2)]),
 dict(key="PCR4", badge="PCR4", zone="杂交捕获区", z=4,
   what="探针杂交、磁珠捕获与洗脱，把目标基因区域从全基因组文库里富集出来。设备品类最多的一间（21 项），全是台面器械，没有大型落地设备。",
   cond="房间尺寸容得下 21 项台面器械，无需为大型设备预留落地空间。",
   gear=[("PCR 扩增仪",1),("垂直混匀仪",1),("恒温混匀仪",1),("高速离心机",1),("荧光定量仪",1),("磁力架 ×2",2)]),
 dict(key="PCR5", badge="PCR5", zone="文库扩增与检测区", z=5,
   what="捕获后文库扩增，以及上机前质检——毛细管电泳看片段分布、荧光定量测浓度，两项都合格才能上机。",
   cond="位于分区下游、独立成间，与上游建库各间物理分离。",
   gear=[("毛细管电泳仪 Qsep1",1),("荧光定量仪",1),("PCR 扩增仪",1),("冷藏冷冻箱",1)]),
 dict(key="PCR8", badge="PCR8", zone="测序区", z=6,
   what="MGISEQ-2000 上机测序，Halos 一体机完成数据分析与报告解读。全流程终点，设备只有 3 项。",
   cond="位于流程末端，与建库各间物理分离，扩增产物不会反向污染上游。",
   gear=[("MGISEQ-2000 测序仪",1),("Halos 分析解读一体机",1),("抽湿机",1)]),
]

# ---------- 设备清单 ----------
ws=openpyxl.load_workbook(UP+"f37a786e-_____________________.xlsx",data_only=True).active
data=collections.OrderedDict(); room=None
for r in ws.iter_rows(min_row=2,values_only=True):
    a,b,c,d,e,f,g,h=(list(r)+[None]*8)[:8]
    if c=="产品编码": continue
    if a: room=str(a).strip()
    if room and d:
        data.setdefault(room,[]).append(dict(code=str(c).strip(),prod=str(d).strip(),
            dev=str(f).strip(),spec=("—" if g in (None,"—","-") else str(g).strip()),qty=int(h or 1)))
for R in ROOMS:
    R["n"]=len(data[R["key"]])
    R["rest"]=R["n"]-sum(c for _,c in R["gear"])
    assert R["rest"]>=0, R["key"]
print("设备计数:", {R["key"]:(R["n"],R["rest"]) for R in ROOMS})

# ---------- 流程图 ----------
def node(R, cls):
    chips="".join(f'<span class="chip{" hi" if i==0 else ""}">{E(g)}</span>' for i,(g,_) in enumerate(R["gear"]))
    if R["rest"]: chips+=f'<span class="chip more">另含 {R["rest"]} 项</span>'
    extra=""
    if "skip" in cls:
        extra=('<span class="gaplab" aria-hidden="true">中间隔 2 间<em>PCR6 · PCR7</em></span>')
    return f'''<div class="node{cls}" style="--zc:var(--z{R['z']}); --zs:var(--z{R['z']}s)">
  <div class="nhead"><span class="nno">{E(R['badge'])}</span><h3>{E(R['zone'])}</h3><span class="ncount">设备 {R['n']} 项</span></div>
  <div class="nbody">
    <p class="what">{E(R['what'])}</p>
    <div class="cond"><span class="ck">✓</span><p>{E(R['cond'])}</p></div>
    <div class="gear"><span class="glab">台面主要设备</span><div class="chips">{chips}</div></div>
  </div>{extra}</div>'''

parts=[node(ROOMS[0]," arw"), node(ROOMS[1]," arw"), node(ROOMS[2],""),
       '<div class="wrapline" aria-hidden="true"><span class="wlab">流程接续</span><span class="wtip"></span></div>',
       node(ROOMS[3]," arw"), node(ROOMS[4]," arw skip"), node(ROOMS[5],"")]
FLOW=('<div class="flow" role="group" aria-label="肿瘤 NGS 六个功能间的工艺流程：试剂准备区、标本与文库制备区、'
      '血浆文库制备区、杂交捕获区、文库扩增与检测区、测序区，依次单向推进；文库扩增与检测区与测序区之间'
      '还隔着 PCR6、PCR7 两个本次不使用的房间">'+"".join(parts)+'</div>')

# ---------- 设备表 ----------
rows=[]
for R in ROOMS:
    items=data[R["key"]]; n=sum(i["qty"] for i in items)
    rows.append(f'<tbody><tr class="grp" style="--zc:var(--z{R["z"]}); --zs:var(--z{R["z"]}s)">'
                f'<th colspan="5">{E(R["key"])} · {E(R["zone"])}<span class="mono">{len(items)} 项 / {n} 台件</span></th></tr></tbody>')
    body=[f'<tr><td class="code">{E(i["code"])}</td><td>{E(i["prod"])}</td><td>{E(i["dev"])}</td>'
          f'<td>{E(i["spec"])}</td><td class="num">{i["qty"]}</td></tr>'
          for i in items if i["dev"] not in ("单道移液器","八道移液器")]
    for label in ("单道移液器","八道移液器"):
        grp=[i for i in items if i["dev"]==label]
        if not grp: continue
        rng=[re.sub(r'^.*?移液器','',x["prod"]).strip() for x in grp]
        body.append(f'<tr><td class="code">{E(" / ".join(x["code"] for x in grp))}</td>'
                    f'<td>TIANGEN {E(label)}　<span class="mono" style="font-size:12px;color:var(--muted)">{E(" · ".join(rng))}</span></td>'
                    f'<td>{E(label)}</td><td>—</td><td class="num">{len(grp)}</td></tr>')
    rows.append("<tbody>"+"".join(body)+"</tbody>")

# ---------- 试剂盒 ----------
ws2=openpyxl.load_workbook(UP+"165b8495-___________.xlsx",data_only=True).active
kr=[]
for r in ws2.iter_rows(min_row=2,values_only=True):
    no,name,mfr,reg,scope,ext,bar,price=(list(r)+[None]*8)[:8]
    if not no: continue
    kr.append(f'''<tr><td class="num" style="text-align:left">{E(str(no))}</td>
      <td class="w"><b>{E(str(name).strip())}</b><br><span style="font-size:12px;color:var(--muted)">{E(str(mfr).strip())}</span></td>
      <td class="code">{E(str(reg).strip())}</td><td style="min-width:6em">{E(str(scope).strip())}</td>
      <td class="w" style="font-size:12.5px;color:var(--ink-2)">{E((str(ext).strip() if ext else "") or "—")}</td>
      <td class="num"><b>{int(price):,}</b> 元</td></tr>''')
kits=('<thead><tr><th>#</th><th>试剂盒 / 生产厂家</th><th>注册证号</th><th>注册适用范围</th>'
      '<th>可拓展适用范围</th><th style="text-align:right">物价收费</th></tr></thead><tbody>'+"".join(kr)+'</tbody>')


# ---------- 其他已注册可选试剂盒（参考，公开注册信息核对） ----------
REF=[
 ("国械注准20183400507","人类10基因突变联合检测试剂盒（可逆末端终止测序法）","厦门艾德生物医药科技股份有限公司",
  "非小细胞肺癌、结直肠癌",
  "EGFR / ALK / ROS1 / RET / KRAS / NRAS / PIK3CA / BRAF / HER2 / MET 十基因联检；2018 年经创新医疗器械特别审批通道获批，为国内较早获批的肿瘤 NGS 产品之一"),
 ("国械注准20193400099","人BRCA1/BRCA2基因突变检测试剂盒（可逆末端终止测序法）","厦门艾德生物医药科技股份有限公司",
  "卵巢癌、乳腺癌、前列腺癌",
  "检测编码区、外显子-内含子连接区与 UTR 区的点突变、插入缺失及纯合缺失；用于 PARP 抑制剂的伴随诊断"),
]
refrows="".join(
  f'<tr><td class="code">{E(a)}</td>'
  f'<td class="w"><b>{E(b)}</b><br><span style="font-size:12px;color:var(--muted)">{E(c)}</span></td>'
  f'<td style="min-width:7em">{E(d)}</td>'
  f'<td class="w" style="font-size:12.5px;color:var(--ink-2)">{E(e)}</td></tr>' for a,b,c,d,e in REF)
REFTBL=('<thead><tr><th>注册证编号</th><th>试剂盒 / 生产厂家</th><th>注册适用范围</th><th>说明</th></tr></thead>'
        '<tbody>'+refrows+'</tbody>')

t=open("tpl3.html",encoding="utf-8").read()
for k,v in (("__FLOW__",FLOW),("__EQUIP__","\n".join(rows)),("__KITS__",kits),("__REF__",REFTBL)):
    assert k in t, k
    t=t.replace(k,v)
for banned in ("现场门牌","落位要点","非按比例平面图","我方","院方"):
    assert banned not in t, f"残留措辞：{banned}"
open("ngs-lab.html","w",encoding="utf-8").write(t)
print("written", len(t), "bytes")
