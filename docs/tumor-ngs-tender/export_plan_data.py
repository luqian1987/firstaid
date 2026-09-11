# -*- coding: utf-8 -*-
"""服务内容版 Word 所需数据，与 HTML 版同源"""
import json, importlib.util, io, contextlib
spec=importlib.util.spec_from_file_location("bp","build_plan.py")
bp=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(bp)
bt=bp.bt
groups=[]; total=0; qty=0
for R in bt.D["rooms"]:
    rows=[[dev, bt.GENERIC.get(dev,sp), n, bp.USE[dev]]
          for dev,sp,ref,n in R["rows"] if dev not in bt.SEQ]
    if rows:
        groups.append(dict(zone=R["zone"], step=bp.STEP[R["zone"]], rows=rows)); total+=len(rows); qty+=sum(r[2] for r in rows)
tech=[(t, d.replace('<b>','**').replace('</b>','**')) for t,d in bt.TECH]
json.dump(dict(tech=tech, proj=bt.PROJ, emerg=bp.EMERG, groups=groups, total=total, qty=qty),
          open("plan_docx_data.json","w"), ensure_ascii=False, indent=1)
