# -*- coding: utf-8 -*-
"""郭 9.13 设备清单（对照 szwzf 9.12 标色）— 屏幕/打印用 HTML"""
import json, html, subprocess, re
E=html.escape
subprocess.run(["python3","cmp_equip.py"],check=True,capture_output=True)
D=json.load(open("equip_cmp.json",encoding="utf-8"))

TAG={"新房间":("add","新增"),"新增":("add","新增"),"移入":("move","调入"),
     "修改":("chg","修改"),"未变":("",""),}
ZONE_NOTE={
 "PCR4文库制备区":"原「PCR4 破碎区」与「PCR5 文库制备区」合并为一间，片段化与建库同区完成",
 "PCR5扩增一区":"原「PCR5 文库制备区」腾出，改作文库预扩增",
 "PCR7扩增二区":"原「PCR7 扩增区」，上机前质检移出",
 "PCR9电泳":"新增分区，承接原 PCR7 的上机前质检",
}
rows=[]
for g in D["groups"]:
    h=g["hdr"]; n=len(g["rows"])
    mk=[]
    if h["room_new"]: mk.append('<span class="p add">新增分区</span>')
    if h["room_changed"]: mk.append(f'<span class="p chg">改名</span> <s>{E(h["room_old"])}</s>')
    if h["step_changed"]: mk.append(f'<span class="p chg">步骤</span> <s>{E(h["step_old"])}</s>')
    note=ZONE_NOTE.get(h["room"],"")
    rows.append(f'<tr class="grp"><td colspan="6"><b>{E(h["room"])}</b>　<span class="stp">{E(h["step"])}</span>'
                + ("　"+"　".join(mk) if mk else "")
                + (f'<div class="nt">{E(note)}</div>' if note else "") + '</td></tr>')
    for r in g["rows"]:
        cls,lab=TAG[r["tag"]]
        badge=f'<span class="p {cls}">{lab}</span>' if lab else ""
        old=""
        if r["tag"]=="修改":
            old='<div class="old">原：'+"；".join(
                f'{E(a)} {E(b) or "（空）"}' for a,b,c in r["diff"])+'</div>'
        todo='<span class="p todo">待补</span>' if r.get("todo") else ""
        rows.append(f'<tr class="{cls}"><td>{E(r["dev"])}{badge}{todo}</td>'
                    f'<td>{E(r["ven"]) or "—"}</td><td>{E(r["mod"]) or "—"}{old}</td>'
                    f'<td class="c">{E(r["qty"])}</td><td>{E(r["use"]) or "—"}</td>'
                    f'<td class="c">{lab or "—"}</td></tr>')
    for x in h.get("gone",[]):
        to=("移至 PCR"+"／PCR".join(str(i) for i in x["moved_to"])) if x["moved_to"] else "已删除"
        rows.append(f'<tr class="del"><td colspan="6"><s>{E(x["dev"])}</s>　'
                    f'<span class="p del">移出</span>{E(to)}</td></tr>')

t=open("diff_tpl.html",encoding="utf-8").read().replace("__ROWS__","".join(rows))
_root=re.search(r":root\{(.*?)\}",t,re.S).group(1)
assert not (set(re.findall(r"var\((--[a-z0-9-]+)\)",t)) - set(re.findall(r"(--[a-z0-9-]+)\s*:",_root)))
open("ngs-equip-diff.html","w",encoding="utf-8").write(t)
n=sum(len(g["rows"]) for g in D["groups"])
print(f"written · {len(D['groups'])} 分区 / {n} 行")
