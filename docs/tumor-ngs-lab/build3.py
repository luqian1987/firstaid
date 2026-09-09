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
 ("国械注准20193400099","人类BRCA1基因和BRCA2基因突变检测试剂盒（可逆末端终止测序法）","厦门艾德生物医药科技股份有限公司",
  "卵巢癌、乳腺癌",
  "检测 BRCA1 / BRCA2 编码区、外显子-内含子连接区、UTR 区与启动子区的点突变、插入缺失及纯合缺失；用于帕米帕利等 PARP 抑制剂的用药指导"),
 ("国械注准20253402685","人BRCA1/BRCA2基因突变检测试剂盒（可逆末端终止测序法）","厦门艾德生物医药科技股份有限公司",
  "前列腺癌",
  "用于携带胚系和 / 或体系 BRCA 基因突变的转移性去势抵抗性前列腺癌（mCRPC）；泽倍珂®（尼拉帕利阿比特龙片）的伴随诊断"),
]
refrows="".join(
  f'<tr><td class="code">{E(a)}</td>'
  f'<td class="w"><b>{E(b)}</b><br><span style="font-size:12px;color:var(--muted)">{E(c)}</span></td>'
  f'<td style="min-width:7em">{E(d)}</td>'
  f'<td class="w" style="font-size:12.5px;color:var(--ink-2)">{E(e)}</td></tr>' for a,b,c,d,e in REF)
REFTBL=('<thead><tr><th>注册证编号</th><th>试剂盒 / 生产厂家</th><th>注册适用范围</th><th>说明</th></tr></thead>'
        '<tbody>'+refrows+'</tbody>')


# ---------- NGS 临床应用方向（大类） ----------
DIRS=[
 dict(t="实体瘤精准诊疗", now=True, st=("ok","已有注册产品"),
  d="靶向与免疫治疗的伴随诊断：驱动基因突变、基因融合、肿瘤突变负荷（TMB）、微卫星不稳定（MSI）与同源重组缺陷（HRD）。国内已注册产品最多的方向。"),
 dict(t="遗传性肿瘤易感基因", now=False, st=("ok","已有注册产品"),
  d="BRCA1 / BRCA2 等胚系突变筛查，用于高危人群管理、亲属级联筛查与 PARP 抑制剂用药指导。第三节参考表所列两项即属此类。"),
 dict(t="血液系统肿瘤分子分型", now=False, st=("part","部分已有注册产品"),
  d="白血病、淋巴瘤、骨髓增生异常综合征的融合基因与突变谱检测，用于分型、危险度分层与疗效监测。微小残留病（MRD）监测目前多以自建项目开展。"),
 dict(t="生殖健康与出生缺陷防控", now=False, st=("ok","已有注册产品"),
  d="无创产前筛查（NIPT）、染色体拷贝数变异检测（CNV-seq）、胚胎植入前遗传学检测（PGT）。NIPT 是国内最早获批的 NGS 临床应用方向。"),
 dict(t="单基因遗传病与携带者筛查", now=False, st=("part","部分已有注册产品"),
  d="地中海贫血、遗传性耳聋等常见单基因病已有注册试剂盒；更广的多基因 panel 与全外显子组测序目前多以自建项目路径开展。"),
 dict(t="感染性疾病病原检测", now=False, st=("ldt","多以 LDT 路径开展"),
  d="宏基因组测序（mNGS）与靶向测序（tNGS），用于疑难危重感染的病原快速识别。测序平台已取得三类注册证，国内已发布多部临床应用专家共识。"),
]
TAG = '<span class="dtag">本次项目</span>'
def _dir(x):
    tag = TAG if x["now"] else ""
    cls = " now" if x["now"] else ""
    return (f'<div class="dir{cls}"><div class="dtop"><h4>{E(x["t"])}</h4>{tag}</div>'
            f'<p>{E(x["d"])}</p>'
            f'<span class="dpill {x["st"][0]}">{E(x["st"][1])}</span></div>')
DIRHTML="".join(_dir(x) for x in DIRS)

t=open("tpl3.html",encoding="utf-8").read()
for k,v in (("__FLOW__",FLOW),("__EQUIP__","\n".join(rows)),("__KITS__",kits),("__REF__",REFTBL),("__DIRS__",DIRHTML)):
    assert k in t, k
    t=t.replace(k,v)

# 变量守卫：页面里用到的每个 CSS 变量，都必须在裸 :root 块里定义过
_root = re.search(r":root\{(.*?)\}", t, re.S).group(1)
_defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", _root))
_used = set(re.findall(r"var\((--[a-z0-9-]+)\)", t))
_inline = {"--zc","--zs"}          # 由节点 style 属性就地赋值，不进 :root
_missing = sorted(_used - _defined - _inline)
assert not _missing, f"CSS 变量未在 :root 定义：{_missing}"

for banned in ("现场门牌","落位要点","非按比例平面图","我方","院方"):
    assert banned not in t, f"残留措辞：{banned}"
open("ngs-lab.html","w",encoding="utf-8").write(t)
print("written", len(t), "bytes")
