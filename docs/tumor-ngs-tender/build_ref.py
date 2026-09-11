# -*- coding: utf-8 -*-
"""照参照文档体例的对院应答稿：不隐去品牌，测序仪明写 MGISEQ-2000"""
import json, html, re, subprocess
E=html.escape
BLANK='<span class="blank">&nbsp;</span>'
subprocess.run(["python3","extract_equip_raw.py"],check=True,capture_output=True)
G=json.load(open("equip_raw.json",encoding="utf-8"))

TAG=re.compile(r'(<b>.*?</b>|<br>)')
def rich(x):
    """保留 <b> 与 <br>，其余转义"""
    return "".join(s if TAG.fullmatch(s) else E(s)
                   for s in TAG.split(x)).replace("＿＿", BLANK)

# 应急事件按肿瘤 NGS 的真实风险点重排：无危急值（报告以日计，非即时项目），
# 无院区间标本物流（检测集中在总院，样本获取由院方负责）；
# 增列样本质量／建库失败与报告超期，这两项是本类项目最高频的中断来源
EMERG=[
 ("测序仪等核心设备故障",
  "1. 按合同约定时限响应与到场，现场维修或返厂维修后交还医院；<br>"
  "2. 无法在约定时限内修复的，提供同等性能备机或其他替代方案，保障在院检测的连续性。"),
 ("试剂与耗材供应中断",
  "1. 建立安全库存，提前告知供应风险；<br>"
  "2. 由中标方其他仓库临时调拨，并联系厂家及时恢复供应。"),
 ("样本质量不合格或建库、捕获失败",
  "1. 出具不合格原因说明与相应质控数据；<br>"
  "2. 需重新取材的，配合院方完成样本补充。"),
 ("检测报告超期",
  "1. 提前告知延期原因与预计出报告时间；<br>"
  "2. 因中标方设备、试剂或技术支持原因导致超期的，按合同约定承担责任并提出改进措施。"),
 ("检测结果争议与复核",
  "1. 配合院方开展原因调查，提供批次记录、质控数据与方法学资料；<br>"
  "2. 必要时以原样本重新检测或以其他方法学验证，并补充更新防范措施。"),
 ("数据或分析系统异常",
  "1. 及时响应，协助完成数据恢复与追溯，并出具书面说明；<br>"
  "2. 涉及数据完整性的，配合院方开展核查。"),
]
emerg="".join(f'<tr><td>{E(a)}</td><td>{b}</td></tr>' for a,b in EMERG)

BID=[("＿＿＿＿（投标方名称）",
      "设备：附件一整包投入<br>试剂：不高于对应检测项目收费标准的 ＿＿ ％",
      "1. 测序仪为华大智造 MGISEQ-2000，1 台，服务期内不更换；<br>"
      "2. 设备所有权自最终验收合格之日起归院方所有；<br>"
      "3. 所供设备提供终身免费维保；<br>"
      "4. 试剂收费标准按江苏省现行医疗服务价格政策执行，后续政策如进一步调整，双方根据实际情况友好协商；<br>"
      "5. 院方场地调整需要院内移机的，移机服务价格单独报出（可根据实际情况减免），"
      "移机不影响维保责任的连续承担。")]
bid="".join(f'<tr><td>{rich(a)}</td><td>{rich(b)}</td><td>{rich(c)}</td></tr>' for a,b,c in BID)

eq=[]; n=0; q=0
for g in G:
    rows=g["rows"]; n+=len(rows); q+=sum(r[3] for r in rows)
    for k,(dev,ven,mod,qty,use) in enumerate(rows):
        # 试剂准备间的房号与分区名同义，只显示一次
        rm=f'{E(g["room"])}<br>{E(g["zone"])}' if g["room"]!=g["zone"].rstrip("区")+"间" else E(g["room"])
        lead=(f'<td rowspan="{len(rows)}">{rm}</td>'
              f'<td rowspan="{len(rows)}">{E(g["step"])}</td>') if k==0 else ""
        eq.append(f'<tr>{lead}<td>{E(dev)}</td><td>{E(ven)}</td><td>{E(mod)}</td>'
                  f'<td class="c">{qty}</td><td>{E(use)}</td></tr>')

t=open("tender_head.html",encoding="utf-8").read().replace(
    "<title>肿瘤NGS板块汇报打印稿</title>","<title>肿瘤NGS平台招标需求（对院应答稿）</title>",1) \
  + open("ref_body.html",encoding="utf-8").read()
for k,v in (("__EMERG__",emerg),("__BID__",bid),("__EQUIP__","".join(eq)),
            ("__N__",str(n)),("__Q__",str(q))):
    assert k in t, k
    t=t.replace(k,v)
t=t.replace("＿＿", BLANK)

# 版式守卫：CSS 变量必须有定义，且全文保持黑白
_root=re.search(r":root\{(.*?)\}",t,re.S).group(1)
assert not (set(re.findall(r"var\((--[a-z0-9-]+)\)",t)) - set(re.findall(r"(--[a-z0-9-]+)\s*:",_root)))
_css=t[t.index("<style>"):t.index("</style>")]
assert not [h for h in set(re.findall(r"#([0-9A-Fa-f]{6})\b",_css))
            if not h[0:2].lower()==h[2:4].lower()==h[4:6].lower()], "出现彩色"
# 本稿对院不隐去品牌，但仍不得出现参照文本中他方的商业信息与内部会议措辞
for banned in ("金域","迪安","金匙","扣率","一票否决","郭博","翟主任","李璟欣","吕主任",
               "郑老师","吴院长","八楼","人员待遇由公司",
               # 以下为参照文档针对 mNGS 外送模式的内容，不适用于本项目
               "危急值","危重病人","医疗纠纷","物流运输应急","标本运输","院区间","2人2车"):
    assert banned not in t, f"不应出现：{banned}"
# 全文以「中标方／投标方」自称，不得出现第一人称
assert "我方" not in t and "我司" not in t and "供应商" not in t
# 测序仪唯一，且明写机型
assert t.count("MGISEQ-2000")>=2 and "MGISEQ-200<" not in t
# 标签未被转义成字面文本
assert "&lt;br" not in t and "&lt;b&gt;" not in t
open("ngs-ref.html","w",encoding="utf-8").write(t)
print(f"written {len(t)} chars · 应急 {len(EMERG)} 条 · 清单 {n} 行／{q} 台件")
