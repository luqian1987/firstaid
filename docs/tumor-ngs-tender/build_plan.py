# -*- coding: utf-8 -*-
"""服务内容体例版：与招标需求版同源，按参照文本的结构呈现"""
import json, html, re, importlib.util, io, contextlib
E=html.escape
BLANK='<span class="blank">&nbsp;</span>'
spec=importlib.util.spec_from_file_location("bt","build_tender.py")
bt=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(bt)

def rich(x):
    return "".join(s if s.startswith('<b>') else E(s)
                   for s in re.split(r'(<b>.*?</b>)', x)).replace("＿＿", BLANK)

tech="".join(f'<tr><td class="c">{i}</td><td>{E(t)}</td><td>{rich(d)}</td></tr>'
             for i,(t,d) in enumerate(bt.TECH,1))
proj="".join(f'<tr><td class="c">{i}</td><td>{E(t)}</td><td>{E(d)}</td></tr>'
             for i,(t,d) in enumerate(bt.PROJ,1))

EMERG=[
 ("核心设备故障","按合同约定时限响应与到场；无法在约定时限内修复的，提供同等性能备机，"
  "或协助将标本委托至具备临床基因扩增检验实验室资质及相应检测项目能力的第三方医学检验机构检测，"
  "委托检验须另行签订协议并报院方备案。"),
 ("试剂或耗材供应中断","建立安全库存并提前告知供应风险；发生中断的，及时提出替代方案，"
  "因供应中断导致检测延误的，按合同约定承担责任。"),
 ("危急值与加急标本","按院方危急值管理制度优先处理并复核确认，结果电话通知至临床并留存记录。"),
 ("数据或分析系统异常","及时响应，协助完成数据恢复与追溯，并出具书面说明；"
  "涉及数据完整性的，配合院方开展核查。"),
 ("检验质量争议","配合院方开展原因调查，提供批次记录、质控数据与方法学资料；"
  "确因产品或服务原因造成损失的，按合同约定承担责任并提出纠正措施。"),
]
emerg="".join(f'<tr><td>{E(a)}</td><td>{E(b)}</td></tr>' for a,b in EMERG)

# 附件一：补「步骤」与「用途」两列，对齐参照文本的表结构
STEP={"试剂准备区":"试剂配制与分装",
      "标本与文库制备区":"核酸提取 + 文库构建（扩增前）",
      "血浆文库制备区":"血浆 cfDNA 提取与文库构建",
      "杂交捕获区":"探针杂交与磁珠捕获",
      "文库扩增与检测区":"捕获后扩增与上机前质检",
      "测序区":"上机测序与数据分析"}
USE={"超净工作台":"试剂配制","纯水仪":"实验用水制备","冷藏冷冻箱":"试剂与样本暂存",
     "计时器":"流程计时","温湿度计":"环境监测","漩涡振荡器":"混匀","掌式离心机":"瞬时离心",
     "单道移液器":"分子实验常规器具","八道移液器":"分子实验常规器具",
     "生物安全柜（A2型）":"开放性生物样本操作","PCR扩增仪":"文库孵育与扩增",
     "高速离心机":"纯化与分离","磁力架":"磁珠纯化","96孔磁力架（八排管）":"磁珠纯化（96 孔）",
     "恒温混匀仪":"温控孵育与混匀","垂直混匀仪":"杂交孵育混匀",
     "荧光定量仪":"核酸与文库浓度测定","全自动毛细管电泳仪":"文库片段分布分析",
     "抽湿机":"环境湿度控制","分析解读一体机":"数据分析与报告解读"}
eq=[]; total=0
for R in bt.D["rooms"]:
    rows=[(dev,sp,qty) for dev,sp,ref,qty in R["rows"] if dev not in bt.SEQ]
    if not rows: continue
    total+=len(rows)
    for k,(dev,sp,qty) in enumerate(rows):
        cells=""
        if k==0:
            cells=(f'<td rowspan="{len(rows)}">{E(R["zone"])}</td>'
                   f'<td rowspan="{len(rows)}">{E(STEP[R["zone"]])}</td>')
        eq.append(f'<tr>{cells}<td>{E(dev)}</td><td>{E(bt.GENERIC.get(dev,sp))}</td>'
                  f'<td class="c">{qty}</td><td>{E(USE.get(dev,"分子实验常规器具"))}</td></tr>')

t=open("tender_head.html",encoding="utf-8").read().replace(
    "<title>肿瘤NGS板块汇报打印稿</title>","<title>肿瘤NGS平台建设需求</title>",1) \
  + open("plan_body.html",encoding="utf-8").read()
t=t.replace("本清单按功能分区列明，共 ＿＿ 项", f"本清单按功能分区列明，共 {total} 项")
for k,v in (("__TECH__",tech),("__PROJ__",proj),("__EMERG__",emerg),("__EQUIP__","".join(eq))):
    assert k in t, k
    t=t.replace(k,v)
t=t.replace("＿＿", BLANK)

_root=re.search(r":root\{(.*?)\}",t,re.S).group(1)
assert not (set(re.findall(r"var\((--[a-z0-9-]+)\)",t)) - set(re.findall(r"(--[a-z0-9-]+)\s*:",_root)))
_css=t[t.index("<style>"):t.index("</style>")]
assert not [h for h in set(re.findall(r"#([0-9A-Fa-f]{6})\b",_css))
            if not h[0:2].lower()==h[2:4].lower()==h[4:6].lower()], "出现彩色"
for banned in ("华大","MGISEQ","MGI","Halos","TIANGEN","病理科","八楼","金域","迪安","金匙",
               "意向公司","科研支持","项目推广","人员待遇","PCR2","PCR8","扣率","挂牌价","五折"):
    assert banned not in t, f"出现不应展示的内容：{banned}"
open("ngs-plan.html","w",encoding="utf-8").write(t)
print(f"written {len(t)} bytes · 测序仪 {len(bt.TECH)} 项 · 应急 {len(EMERG)} 条 · 清单 {total} 行")
