# -*- coding: utf-8 -*-
import json, html, re
E=html.escape
D=json.load(open("tender_data.json"))
BLANK='<span class="blank">&nbsp;</span>'
def fill(x): return E(x).replace("＿＿", BLANK)

# 测序仪：以资质与功能性指标描述，不写机型参数
TECH=[
 ("注册资质","所投产品应为已取得国家药品监督管理局第三类医疗器械注册证的临床用高通量基因测序仪，注册证在有效期内。"),
 ("测序原理","不限。"),
 ("配套试剂的注册匹配","所投测序仪应具备可配套使用的、已取得第三类医疗器械注册证的肿瘤检测试剂盒。"
  "投标人须<b>就附件二所列的每一癌种分别列明</b>对应试剂盒的名称与注册证编号，"
  "并提供注册证复印件；<b>试剂盒注册证载明的适用机型应包含所投机型</b>。"),
 ("建库方法学","所投试剂盒应采用<b>杂交捕获富集法</b>建库，支持点突变、插入缺失、基因融合与拷贝数变异的同步检测。"
  "组织样本基因组 DNA 的片段化<b>采用酶法或物理超声法均可，本项目不作限定</b>；"
  "附件一已按物理超声法预留片段化设备并单独设置破碎区，"
  "投标人应按所投试剂盒的实际方法学一并供应相应设备，并提出其安装与环境条件要求。"),
 ("样本类型","应支持<b>肿瘤组织（FFPE）与外周血血浆游离 DNA（cfDNA）两类样本</b>的检测，"
  "且两类样本均具备对应的已注册检测试剂盒。"),
 ("检测能力","单次运行可同时检测的样本数不少于 ＿＿ 例。"),
 ("数据分析","应配置与所投试剂盒相匹配的生物信息分析与报告解读软件或软硬件一体设备，"
  "支持院内本地化部署，不得要求将原始数据上传至院外。"),
 ("环境与配套","投标人须提供设备的供电、温湿度、承重、给排水与网络接入要求，"
  "并说明是否需要配置不间断电源；相关配套条件的适配由中标人负责。"),
 ("数量","1 台。"),
]
def rich(x):
    out=[]
    for seg in re.split(r'(<b>.*?</b>)', x):
        out.append(seg if seg.startswith('<b>') else E(seg))
    return "".join(out).replace("＿＿", BLANK)
tech="".join(f'<tr><td class="c">{i}</td><td>{E(t)}</td><td>{rich(d)}</td></tr>' for i,(t,d) in enumerate(TECH,1))

PROJ=[
 ("非小细胞肺癌","EGFR、ALK、ROS1 等基因的点突变、插入缺失与基因融合。"),
 ("结直肠癌","KRAS、NRAS、BRAF 等基因的点突变与插入缺失。"),
 ("乳腺癌","BRCA1／BRCA2、PIK3CA 等基因的点突变与插入缺失。"),
]
proj="".join(f'<tr><td class="c">{i}</td><td>{E(t)}</td><td>{E(d)}</td></tr>' for i,(t,d) in enumerate(PROJ,1))

# 附件一：去掉品牌型号列，去掉测序仪（已在正文第二部分），分区名不带房间号
SEQ={"MGISEQ-2000 基因组测序仪"}
GENERIC={"分析解读一体机":"分析解读服务器或一体机，支持院内本地化部署，与所投试剂盒配套的生物信息分析与报告解读"}
eq=[]; total=0; qty=0
for R in D["rooms"]:
    rows=[(dev,sp,n) for dev,sp,ref,n in R["rows"] if dev not in SEQ]
    if not rows: continue
    total+=len(rows); qty+=sum(n for *_,n in rows)
    eq.append(f'<tr class="grp"><td colspan="3">{E(R["zone"])}</td></tr>')
    for dev,sp,n in rows:
        eq.append(f'<tr><td>{E(dev)}</td><td>{E(GENERIC.get(dev,sp))}</td><td class="c">{n}</td></tr>')

t=open("tender_head.html",encoding="utf-8").read().replace(
    "<title>肿瘤NGS板块汇报打印稿</title>","<title>肿瘤NGS平台招标需求</title>",1) \
  + open("tender_body.html",encoding="utf-8").read()
_n="本清单按功能分区列明，共 ＿＿ 项"
assert t.count(_n)==1, "附件一项数占位符未命中"
t=t.replace(_n, f"本清单按功能分区列明，共 {total} 项、{qty} 台（件）")
for k,v in (("__TECH__",tech),("__PROJ__",proj),("__EQUIP__","".join(eq))):
    assert k in t, k
    t=t.replace(k,v)
t=t.replace("＿＿", BLANK)

_root=re.search(r":root\{(.*?)\}",t,re.S).group(1)
_def=set(re.findall(r"(--[a-z0-9-]+)\s*:",_root)); _used=set(re.findall(r"var\((--[a-z0-9-]+)\)",t))
assert not (_used-_def), sorted(_used-_def)
_css=t[t.index("<style>"):t.index("</style>")]
_col=[h for h in set(re.findall(r"#([0-9A-Fa-f]{6})\b",_css)) if not h[0:2].lower()==h[2:4].lower()==h[4:6].lower()]
assert not _col, f"出现彩色：{_col}"
# 对外文件守卫：不得出现品牌、内部科室、内部会议信息与已否决的条款
for banned in ("华大","MGISEQ","MGI","Halos","TIANGEN","病理科","八楼","一票否决",
               "金域","迪安","金匙","意向公司","科研支持","项目推广",
               "人员待遇","PCR2","PCR3","PCR4","PCR5","PCR6","PCR7","PCR8","郭博","翟主任",
               "世和","宜兴","Covaris","Qubit","MagSH","Fluo","Qsep","碳环","澳柯玛","湘仪",
               "东胜龙","锐思捷","雨花泽","苏净","瑞诚","拓赫","光鼎","欧井","洛可可","H3C",
               "予以沿用","缺配清单","院方自备设备",
               "微卫星不稳定","MSI","错配修复","dMMR","TMB"):   # 方法学或注册状态与本平台不符，勿写入
    assert banned not in t, f"对外文件中出现不应展示的内容：{banned}"
# 「折扣率」是本文件的正当用语，只禁止单独出现的「扣率」（参照文本中的供应商报价扣率）
for w in ("扣率", "挂牌价", "挂网价", "五折"):
    assert w not in t, f"试剂报价已改为与物价收费标准挂钩，不应再出现：{w}"

# 需求文件的边界：以下属招标文件的合同章节或采购部门通用模板，不在采购需求内
for pat, what in ((r"日历天", "交货日历天数"),
                  (r"质量保证金", "质量保证金比例"),
                  (r"支付\s*(?:<span|＿＿)\s*％", "付款比例分档"),
                  (r"近\s*(?:<span|＿＿)\s*年", "业绩年限要求"),
                  (r"本地化服务能力", "本地化服务能力"),
                  (r"失信被执行人|严重违法失信|商业贿赂不良记录", "失信名单资格条款"),
                  (r"不超过\s*(?:<span|＿＿)\s*小时", "响应与到场时限"),
                  (r"违约与退出", "违约与退出条款")):
    assert not re.search(pat, t), f"需求文件中出现应留给合同的内容：{what}"
open("ngs-tender.html","w",encoding="utf-8").write(t)
print(f"written {len(t)} chars · 测序仪要求 {len(TECH)} 项 · 拟开展癌种 {len(PROJ)} 个 · 配套清单 {total} 行／{qty} 台件")
