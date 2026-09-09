# -*- coding: utf-8 -*-
import json, html, re
E=html.escape
D=json.load(open("tender_data.json"))

TECH=[
 ("注册资质","所投产品应为已取得国家药品监督管理局第三类医疗器械注册证的临床用高通量基因测序系统，注册证在有效期内，且经营范围与授权文件齐备。"),
 ("测序原理","不限。"),
 ("单次运行数据产出","≥ ＿＿ Gb。"),
 ("支持读长","支持双端 100 bp 及以上读长。"),
 ("单次运行样本通量","≥ ＿＿ 例（按拟开展 panel 规模测算）。"),
 ("单次运行时长","≤ ＿＿ 小时。"),
 ("配套试剂注册状态","可配套使用的检测试剂盒应已取得第三类医疗器械注册证，且注册证载明的适用机型包含所投机型。投标人须逐项列明试剂盒名称与注册证编号。"),
 ("数据分析","应配置与所选试剂盒相匹配的分析解读软件或软硬件一体设备，支持院内本地化部署，不得要求将原始数据上传至院外。"),
 ("平台开放性","投标人须如实说明所投平台为封闭系统或开放系统，并明确可使用的检测试剂来源范围。"),
 ("环境与配套","投标人须提供设备的供电、温湿度、承重与网络接入要求，并说明是否需要配置不间断电源。"),
 ("数量","1 台。"),
]
BLANK = '<span class="blank">&nbsp;</span>'
def fill(x): return E(x).replace("＿＿", BLANK)   # 转义后再替换填空标记
tech="".join(f'<tr><td class="c">{i}</td><td>{E(t)}</td><td>{fill(d)}</td></tr>' for i,(t,d) in enumerate(TECH,1))

EMERG=[
 ("核心设备故障","故障响应与到场时限按第七部分第（四）项执行；无法在约定时限内修复的，应提供同等性能备机，或协助将标本委托至具备临床基因扩增检验实验室资质与相应检测项目能力的第三方医学检验机构检测。委托检验须另行签订协议并报院方医务管理部门备案。"),
 ("试剂与耗材供应中断","中标人应建立安全库存并提前告知供应风险；发生中断的，应在 ＿＿ 小时内提出替代方案，因供应中断导致检测延误的，按合同约定承担违约责任。"),
 ("危急值与加急标本","按院方危急值管理制度优先处理并复核确认，结果电话通知至临床并留存记录。"),
 ("信息系统与数据异常","分析系统或数据链路故障时，中标人应在 ＿＿ 小时内响应；涉及数据完整性的，应协助完成数据恢复与追溯，并出具书面说明。"),
 ("检验质量争议","配合院方开展原因调查，提供批次记录、质控数据与方法学资料；确因产品或服务原因造成损失的，按合同约定承担责任并提出纠正措施。"),
]
emerg="".join(f'<tr><td>{E(a)}</td><td>{fill(b)}</td></tr>' for a,b in EMERG)

eq=[]
for R in D["rooms"]:
    eq.append(f'<tr class="grp"><td colspan="4">{E(R["key"])}　{E(R["zone"])}　（{R["kinds"]} 项）</td></tr>')
    for dev,spec,ref,qty in R["rows"]:
        eq.append(f'<tr><td>{E(dev)}</td><td>{E(spec)}</td><td>{E(ref)}</td><td class="c">{qty}</td></tr>')

kits="".join(f'<tr><td class="c">{E(k["no"])}</td><td>{E(k["name"])}</td><td class="nw">{E(k["reg"])}</td>'
             f'<td>{E(k["scope"])}</td><td class="n">{E(k["price"])} 元</td></tr>' for k in D["kits"])

t=open("tender_head.html",encoding="utf-8").read().replace(
    "<title>肿瘤NGS板块汇报打印稿</title>","<title>肿瘤NGS平台招标需求</title>",1) \
  + open("tender_body.html",encoding="utf-8").read()
for k,v in (("__TECH__",tech),("__EMERG__",emerg),("__EQUIP__","".join(eq)),("__KITS__",kits)):
    assert k in t, k
    t=t.replace(k,v)

_root=re.search(r":root\{(.*?)\}",t,re.S).group(1)
_def=set(re.findall(r"(--[a-z0-9-]+)\s*:",_root)); _used=set(re.findall(r"var\((--[a-z0-9-]+)\)",t))
assert not (_used-_def), sorted(_used-_def)
_css=t[t.index("<style>"):t.index("</style>")]
_col=[h for h in set(re.findall(r"#([0-9A-Fa-f]{6})\b",_css)) if not h[0:2].lower()==h[2:4].lower()==h[4:6].lower()]
assert not _col, f"出现彩色：{_col}"
# 守卫分两级：原文本的定向性内容全文禁止；被删条款的名称只在正文禁止（拟稿说明里要解释为何删除）
_prose = re.sub(r'<div class="(?:dn|warn)">.*?</div>', '', t, flags=re.S)
for banned in ("金域","迪安","金匙","扣率","意向公司","南京金域"):
    assert banned not in t, f"全文残留定向内容：{banned}"
for banned in ("科研支持","项目推广","不能更换","终身免费","低于成本的报价"):
    assert banned not in _prose, f"正文残留应删条款：{banned}"
open("ngs-tender.html","w",encoding="utf-8").write(t)
print("written", len(t), "bytes · 技术要求", len(TECH), "项 · 应急", len(EMERG), "项 · 清单行",
      sum(len(r["rows"]) for r in D["rooms"]))
