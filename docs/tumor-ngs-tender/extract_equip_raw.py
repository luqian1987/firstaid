# -*- coding: utf-8 -*-
"""照参照文档体例：房间｜步骤｜产品名称｜建议厂商｜建议规格型号｜数量｜用途（保留品牌型号）"""
import openpyxl, json, collections

SRC="/root/.claude/uploads/12e5ca2d-7231-5774-9600-1c84384c6276/3d2a747d-20260911____________________________.xlsx"

ROOM={"试剂准备区":("试剂准备间","试剂准备区","试剂配制与分装"),
      "样本制备区（组织）":("PCR2","样本制备区（组织）","组织前处理＋基因组 DNA 提取"),
      "样本制备区（血浆）":("PCR3","样本制备区（血浆）","血浆分离＋游离 DNA 提取"),
      "破碎区":("PCR4","破碎区","基因组 DNA 超声片段化"),
      "文库制备":("PCR5","文库制备区","末端修复＋接头连接＋文库构建"),
      "杂交捕获区":("PCR6","杂交捕获区","探针杂交＋磁珠捕获"),
      "扩增区":("PCR7","扩增区","捕获后扩增＋上机前质检"),
      "测序区":("PCR8","测序区","上机测序＋数据分析")}

# 产品名称（原始清单）→（建议厂商，建议规格型号）
VM={
 "澳柯玛超净工作台":("澳柯玛","ACB-1300V"),
 "锐思捷 UNIQ-G1 纯水仪":("锐思捷","UNIQ-G1"),
 "澳柯玛 YCD-265T 冷藏冷冻箱":("澳柯玛","YCD-265T"),
 "得力计时器":("得力","—"),
 "雨花泽 YHZ-90191 温湿度计":("雨花泽","YHZ-90191"),
 "BGI Top-Mix 多管桌面混匀仪":("华大智造","Top-Mix"),
 "BGI Top-Spin 复合转子离心机":("华大智造","Top-Spin"),
 "东胜龙 ETC-821M 基因扩增仪":("东胜龙","ETC-821M"),
 "湘仪 HT165R 离心机":("湘仪","HT165R"),
 "湘仪 H2050R 大容量高速台式冷冻离心机":("湘仪","H2050R"),
 "碳环智造Mag-16W 1.5mL离心管磁力架":("碳环智造","Mag-16W"),
 "碳环智造Mag-96A 96孔磁力架（八排管）":("碳环智造","Mag-96A"),
 "苏净安泰 BSC-1304ⅡA2 生物安全柜":("苏净安泰","BSC-1304ⅡA2"),
 "恒温混匀仪-瑞诚仪器":("瑞诚仪器","—"),
 "拓赫HS-3垂直混匀仪":("拓赫","HS-3"),
 "全自动毛细管电泳仪/浙江光鼎/规格&Qsep1":("浙江光鼎","Qsep1"),
 "欧井 OJ-501E 抽湿机":("欧井","OJ-501E"),
 "MGISEQ-2000 基因测序仪":("华大智造","MGISEQ-2000"),
 "Halos 肿瘤基因检测数据分析解读 一体机":("华大基因","Halos 一体机"),
 "Qubit 4.0 荧光计（原厂）":("Invitrogen（原厂）","Qubit 4.0"),
 "磁力架（MagSH-16-1.5mL）":("世和（定制）","MagSH-16-1.5mL"),
 "磁力架（5ml（MagSH-16-5mL））":("世和（定制）","MagSH-16-5mL"),
 "磁力架（MagSH-96-0.2ml磁力架+辅助支架）":("世和（定制）","MagSH-96-0.2mL＋辅助支架"),
 "超声波破碎仪 Covaris M220":("Covaris","M220"),
 "真空离心浓缩干燥仪":("待定","待定"),
 "服务器（世和生信分析）":("世和（定制）","待定"),
 "掌式离心机":("—","—"),
}
def pipette(p):     # TIANGEN 移液器按分档合并，型号列并列显示
    for k in ("TIANGEN单道移液器","TIANGEN八道手动移液器"):
        if p.startswith(k): return ("TIANGEN", p[len(k):].strip().replace("µl","µL"))
    return None

USE={"超净工作台":"试剂配制","纯水仪":"实验用水制备","冷藏冷冻箱":"试剂与样本暂存",
 "计时器":"流程计时","温湿度计":"环境监测","漩涡振荡器":"混匀","掌式离心机":"瞬时离心",
 "单道移液器":"分子实验操作常规设备","八道移液器":"分子实验操作常规设备",
 "生物安全柜（A2型）":"开放性生物样本操作","PCR扩增仪":"文库孵育／文库扩增",
 "高速离心机":"纯化与分离","冷冻离心机":"血浆分离","磁力架":"磁珠纯化",
 "96孔磁力架（八排管）":"磁珠纯化（96 孔）","恒温混匀仪":"温控孵育与混匀",
 "垂直混匀仪":"杂交孵育混匀","荧光计":"核酸／文库浓度测定","荧光定量仪":"核酸／文库浓度测定",
 "全自动毛细管电泳仪":"文库片段分布分析","超声波破碎仪":"DNA 片段化",
 "真空离心浓缩干燥仪":"捕获后样本与文库浓缩","抽湿机":"环境湿度控制",
 "MGISEQ-2000 基因组测序仪":"基因测序","分析解读一体机":"数据分析与报告解读",
 "服务器":"生信分析与数据存储"}

ws=openpyxl.load_workbook(SRC,data_only=True)["Sheet2"]
groups=[]; cur=None
for row in ws.iter_rows(values_only=True):
    c=["" if x is None else str(x).strip() for x in row]+[""]*8
    if c[0]=="房间": continue
    if c[1] in ROOM:
        rm,zone,step=ROOM[c[1]]
        cur=collections.OrderedDict(); groups.append(dict(room=rm,zone=zone,step=step,items=cur))
    if c[2] in ("","产品编码") or cur is None: continue
    prod,dev,qty=c[3],c[5],int(float(c[7] or 1))
    vm=pipette(prod) or VM.get(prod)
    assert vm, f"未登记厂商／型号：{prod}"
    assert dev in USE, f"未登记用途：{dev}"
    e=cur.setdefault(dev,{"vendors":[],"models":[],"qty":0,"use":USE[dev]})
    if vm[0] not in e["vendors"]: e["vendors"].append(vm[0])
    if vm[1] not in e["models"]: e["models"].append(vm[1])
    e["qty"]+=qty

out=[]
for g in groups:
    rows=[[dev, "／".join(v["vendors"]), "／".join(v["models"]), v["qty"], v["use"]]
          for dev,v in g["items"].items()]
    out.append(dict(room=g["room"],zone=g["zone"],step=g["step"],rows=rows))
json.dump(out,open("equip_raw.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
for g in out:
    print(f'{g["room"]:<6}{g["zone"]:<14} 行 {len(g["rows"]):>2}  台件 {sum(r[3] for r in g["rows"]):>2}')
print("合计", sum(len(g["rows"]) for g in out), "行 /", sum(r[3] for g in out for r in g["rows"]), "台件")
