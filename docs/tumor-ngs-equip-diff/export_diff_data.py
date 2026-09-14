# -*- coding: utf-8 -*-
"""变更对照 Word 版数据，与 HTML 版同源"""
import json, importlib.util, io, contextlib
spec=importlib.util.spec_from_file_location("bd","build_diff.py")
bd=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(bd)
D=json.load(open("equip_cmp.json",encoding="utf-8"))
def gt(r):
    if not r.get("gtot"): return ""
    a,b=r["gtot"]
    return f'全院合计 {a} → {b}' + ("（未变，仅换分区）" if a==b else f"（{b-a:+d}）")
out=[]
for g in D["groups"]:
    h=g["hdr"]
    out.append(dict(
        room=h["room"], step=h["step"],
        room_old=h["room_old"] if h["room_changed"] else "",
        step_old=h["step_old"] if h["step_changed"] else "",
        room_new=h["room_new"], note=bd.ZONE_NOTE.get(h["room"],""),
        rows=[dict(dev=r["dev"], ven=r["ven"] or "—", mod=r["mod"] or "—",
                   qty=r["qty"], use=r["use"] or "—", tag=r["tag"],
                   todo=bool(r.get("todo")),
                   old="；".join(f'{a} {b or "（空）"}' for a,b,c in r.get("diff",[])) if r["tag"]=="修改" else "",
                   gtot=gt(r))
              for r in g["rows"]],
        gone=[dict(dev=x["dev"], to=("移至 PCR"+"／PCR".join(str(i) for i in x["moved_to"])) if x["moved_to"] else "已删除")
              for x in h.get("gone",[])]))
fmt=lambda by:"；".join(f'{k} {v}' for k,v in by.items() if v)
qty=[dict(dev=m["dev"], old=m["old"], new=m["new"], d=m["new"]-m["old"],
          sby=fmt(m["sby"]), gby=fmt(m["gby"])) for m in D["qty_moves"]]
todos=[dict(room=x["room"], dev=x["dev"], qty=x["qty"],
            ven=(x.get("ref") or ["—","—"])[0] or "—",
            mod=(x.get("ref") or ["—","—"])[1] or "—") for x in D["todos"]]
json.dump(dict(groups=out, qty=qty, todos=todos),
          open("diff_docx_data.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
