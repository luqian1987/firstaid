# -*- coding: utf-8 -*-
"""从 build_tender.py 现场导出 Word 版所需数据，保证与 HTML 版同源"""
import json, importlib.util, io, contextlib
spec=importlib.util.spec_from_file_location("bt","build_tender.py")
m=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
rooms=[]; total=0
for R in m.D["rooms"]:
    rows=[[dev, m.GENERIC.get(dev,sp), qty] for dev,sp,ref,qty in R["rows"] if dev not in m.SEQ]
    if rows: rooms.append(dict(zone=R["zone"], rows=rows)); total+=len(rows)
json.dump(dict(tech=m.TECH, proj=m.PROJ, rooms=rooms, total=total),
          open("tender_docx_data.json","w"), ensure_ascii=False, indent=1)
