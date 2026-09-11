# -*- coding: utf-8 -*-
"""Word 版终检：品牌/内部信息守卫 + 与 HTML 版的关键文本一致性"""
import zipfile,re,sys,html
BAN=["华大","MGISEQ","MGI","Halos","TIANGEN","病理科","八楼","一票否决","金域","迪安","金匙",
     "意向公司","科研支持","项目推广","人员待遇","郭博","翟主任","予以沿用","缺配清单",
     "微卫星不稳定","MSI","错配修复","dMMR","TMB","扣率","挂牌价","挂网价","五折",
     "PCR2","PCR3","PCR4","PCR5","PCR6","PCR7","PCR8","世和","宜兴","Covaris","Qubit","MagSH",
     "Fluo","Qsep","碳环","澳柯玛","湘仪","东胜龙","锐思捷","雨花泽","苏净","瑞诚","拓赫",
     "光鼎","欧井","洛可可","H3C","日历天","质量保证金","本地化服务能力","失信被执行人",
     "违约与退出","评标价","评审因素","投标人资格与合规","廉洁承诺","营业执照","医疗器械经营许可证"]
MUST=["破碎区（核酸片段化）","样本制备区（组织）","样本制备区（血浆）","文库制备区","扩增区",
      "超声波核酸片段化仪","真空离心浓缩仪","采购需求" ,"二〇二六年九月十一日","75 项","118 台（件）"]
def text(p):
    z=zipfile.ZipFile(p); x=z.read("word/document.xml").decode("utf-8")
    x=re.sub(r"</w:p>","\n",x); return html.unescape(re.sub(r"<[^>]+>","",x))
bad=0
for p,must in ((sys.argv[1],MUST),(sys.argv[2],[m.replace("采购需求","建设需求") for m in MUST])):
    t=text(p); print("==",p,len(t),"chars")
    for b in BAN:
        if b in t: print("   ✗ 出现禁用内容：",b); bad+=1
    for m in must:
        if m not in t: print("   ✗ 缺少应有内容：",m); bad+=1
    # 分区必须齐 8 个
    zones=["试剂准备区","样本制备区（组织）","样本制备区（血浆）","破碎区（核酸片段化）",
           "文库制备区","杂交捕获区","扩增区","测序区"]
    print("   分区出现情况：", "".join("✓" if z in t else "✗" for z in zones))
print("FAIL" if bad else "OK — 全部通过")
sys.exit(1 if bad else 0)
