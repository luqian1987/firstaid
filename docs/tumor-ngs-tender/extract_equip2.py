# -*- coding: utf-8 -*-
"""从 20260911 更新版设备清单 Sheet2（重新分区：8 间，含独立破碎区）生成 tender_data.json"""
import openpyxl, json, re, collections

SRC="/root/.claude/uploads/12e5ca2d-7231-5774-9600-1c84384c6276/3d2a747d-20260911____________________________.xlsx"
OLD=json.load(open("tender_data.json",encoding="utf-8"))   # 只取 kits

ZONE={"试剂准备区":"试剂准备区",
      "样本制备区（组织）":"样本制备区（组织）",
      "样本制备区（血浆）":"样本制备区（血浆）",
      "破碎区":"破碎区（核酸片段化）",
      "文库制备":"文库制备区",
      "杂交捕获区":"杂交捕获区",
      "扩增区":"扩增区",
      "测序区":"测序区"}

SEQ={"MGISEQ-2000 基因组测序仪"}     # 测序仪在正文单独成章，不入附件一

# 通用名 + 去品牌型号的参数描述
SPEC={
 "超净工作台":"双人位，垂直单向流；洁净度满足试剂配制要求",
 "纯水仪":"出水电阻率 18.2 MΩ·cm",
 "冷藏冷冻箱":"2–8 ℃ 冷藏与 −20 ℃ 冷冻双温区",
 "计时器":"量程覆盖常规孵育时长，具备定时提醒",
 "温湿度计":"可显示环境温湿度，具备最值记录",
 "漩涡振荡器":"转速可调，支持点动与连续两种模式",
 "掌式离心机":"适配 1.5 mL 离心管与八排管，两种转子",
 "单道移液器":"量程分档覆盖 0.1–1000 µL；分档：0.1–2.0、0.5–10、2–20、10–100、20–200、100–1000 µL",
 "八道移液器":"八通道，与八排管、96 孔板配套；分档：0.5–10、5–50、30–300 µL",
 "PCR扩增仪":"≥96 孔，具备梯度扩增功能",
 "高速离心机":"台式高速离心机，配 1.5 mL 离心管转子",
 "台式高速冷冻离心机":"配 4×方形吊篮转子（适配 5 mL／10 mL 管及 24 孔适配器）与 24×1.5／2 mL 角转子；用于血浆分离",
 "生物安全柜（A2型）":"Ⅱ级 A2 型；外形尺寸约 1500×815×2270 mm",
 "恒温混匀仪":"配 96 孔与 1.5 mL 两种模块，控温可调",
 "垂直混匀仪":"满足杂交孵育过程的持续混匀要求",
 "荧光定量仪":"荧光法核酸与文库浓度精确定量",
 "全自动毛细管电泳仪":"文库片段长度分布与浓度分析",
 "磁力架（1.5 mL 离心管用）":"16 孔，适配 1.5 mL 离心管",
 "磁力架（5 mL 离心管用）":"16 孔，适配 5 mL 离心管；用于血浆游离核酸提取",
 "96 孔磁力架":"适配 96 孔 0.2 mL 板与八排管，含辅助支架",
 "超声波核酸片段化仪":"聚焦超声法核酸片段化，片段长度可调；用于组织基因组 DNA 建库前片段化。"
                    "应具备温控，并由投标人提出独立台位、供电与降噪的安装条件",
 "真空离心浓缩仪":"用于杂交捕获后样本与文库的浓缩",
 "抽湿机":"按实验室实际环境湿度条件配置",
 "分析解读一体机":"分析解读服务器或一体机，支持院内本地化部署，与所投试剂盒配套的生物信息分析与报告解读",
 "生物信息分析服务器":"用于本平台生物信息分析与数据存储，支持院内本地化部署",
}

def canon(prod, dev):
    """(产品名称, 设备名称) → 去品牌的通用设备名"""
    if dev=="磁力架":
        if re.search(r"5\s*ml", prod, re.I) and "1.5" not in prod: return "磁力架（5 mL 离心管用）"
        if "96" in prod: return "96 孔磁力架"
        return "磁力架（1.5 mL 离心管用）"
    return {"96孔磁力架（八排管）":"96 孔磁力架",
            "荧光计":"荧光定量仪",
            "超声波破碎仪":"超声波核酸片段化仪",
            "真空离心浓缩干燥仪":"真空离心浓缩仪",
            "冷冻离心机":"台式高速冷冻离心机",
            "服务器":"生物信息分析服务器"}.get(dev, dev)

ws=openpyxl.load_workbook(SRC,data_only=True)["Sheet2"]
rooms=[]; cur=None
for row in ws.iter_rows(values_only=True):
    c=["" if x is None else str(x).strip() for x in row]+[""]*8
    if c[0]=="房间": continue
    if c[1] in ZONE:                      # 房间标签行：开新分区
        cur=collections.OrderedDict(); rooms.append((ZONE[c[1]],cur))
    if c[2] in ("","产品编码"): continue  # 空行 / 每区重复的表头行
    if cur is None: continue
    prod,dev,qty=c[3],c[5],c[7]
    if dev in SEQ: continue
    name=canon(prod,dev)
    assert name in SPEC, f"未定义参数描述：{name}（原始：{prod} / {dev}）"
    cur[name]=cur.get(name,0)+int(float(qty or 1))

out={"rooms":[{"zone":z,"rows":[[n,SPEC[n],"",q] for n,q in d.items()]} for z,d in rooms],
     "kits":OLD["kits"]}
assert len(out["rooms"])==8, len(out["rooms"])
json.dump(out,open("tender_data.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
tot=sum(len(r["rows"]) for r in out["rooms"])
for r in out["rooms"]:
    print(f'{r["zone"]:<16} 行 {len(r["rows"]):>2}  台件 {sum(x[3] for x in r["rows"]):>2}')
print("合计行数",tot,"／台件",sum(x[3] for r in out["rooms"] for x in r["rows"]))
