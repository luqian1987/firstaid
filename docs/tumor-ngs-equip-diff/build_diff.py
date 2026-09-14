# -*- coding: utf-8 -*-
"""郭 9.13 设备清单（对照 szwzf 9.12 标色）— 屏幕/打印用 HTML"""
import json, html, subprocess, re
E=html.escape
subprocess.run(["python3","cmp_equip.py"],check=True,capture_output=True)
D=json.load(open("equip_cmp.json",encoding="utf-8"))

TAG={"新增":("add","新增"),"调入":("move","调入"),"修改":("chg","修改"),"未变":("",""),}
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
        if r.get("gtot"):
            a,b=r["gtot"]
            old+=('<div class="gt">全院合计 %d → %d%s</div>'
                  % (a,b,"（未变，仅换分区）" if a==b else "（%+d）"%(b-a)))
        rows.append(f'<tr class="{cls}"><td>{E(r["dev"])}{badge}{todo}</td>'
                    f'<td>{E(r["ven"]) or "—"}</td><td>{E(r["mod"]) or "—"}{old}</td>'
                    f'<td class="c">{E(r["qty"])}</td><td>{E(r["use"]) or "—"}</td>'
                    f'<td class="c">{lab or "—"}</td></tr>')
    for x in h.get("gone",[]):
        to=("移至 PCR"+"／PCR".join(str(i) for i in x["moved_to"])) if x["moved_to"] else "已删除"
        rows.append(f'<tr class="del"><td colspan="6"><s>{E(x["dev"])}</s>　'
                    f'<span class="p del">移出</span>{E(to)}</td></tr>')

qm=[]
for m in D["qty_moves"]:
    d=m["new"]-m["old"]
    cls="add" if d>0 else ("del" if d<0 else "")
    fmt=lambda by:"；".join(f'{k} {v}' for k,v in by.items() if v)
    qm.append(f'<tr class="{cls}"><td>{E(m["dev"])}</td><td class="c">{m["old"]}</td>'
              f'<td class="c"><b>{m["new"]}</b></td><td class="c"><b>{d:+d}</b></td>'
              f'<td class="sm">{E(fmt(m["sby"]))}</td><td class="sm">{E(fmt(m["gby"]))}</td></tr>')
td=[]
for x in D["todos"]:
    ref=x.get("ref") or ["—","—"]
    td.append(f'<tr><td>{E(x["room"])}</td><td>{E(x["dev"])}</td><td class="c">{E(x["qty"])}</td>'
              f'<td>{E(ref[0]) or "—"}</td><td>{E(ref[1]) or "—"}</td></tr>')

t=open("diff_tpl.html",encoding="utf-8").read() \
  .replace("__ROWS__","".join(rows)).replace("__QTY__","".join(qm)).replace("__TODO__","".join(td))
_root=re.search(r":root\{(.*?)\}",t,re.S).group(1)
assert not (set(re.findall(r"var\((--[a-z0-9-]+)\)",t)) - set(re.findall(r"(--[a-z0-9-]+)\s*:",_root)))
open("ngs-equip-diff.html","w",encoding="utf-8").write(t)
for k in ("__ROWS__","__QTY__","__TODO__"): assert k not in t, k
n=sum(len(g["rows"]) for g in D["groups"])
print(f"written · {len(D['groups'])} 分区 / {n} 行 / 台件变化 {len(D['qty_moves'])} 项 / 待补 {len(D['todos'])} 行")
