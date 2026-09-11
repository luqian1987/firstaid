# -*- coding: utf-8 -*-
"""对院应答稿 Word 版所需数据，与 HTML 版同源（<br> 拆成多行，<b> 转 **）"""
import json, importlib.util, io, contextlib, re
spec=importlib.util.spec_from_file_location("br","build_ref.py")
br=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(br)
def lines(x): return [s.replace('<b>','**').replace('</b>','**') for s in x.split('<br>')]
G=json.load(open("equip_raw.json",encoding="utf-8"))
json.dump(dict(emerg=[[a,lines(b)] for a,b in br.EMERG],
               bid=[[lines(a),lines(b),lines(c)] for a,b,c in br.BID],
               groups=G,
               total=sum(len(g["rows"]) for g in G),
               qty=sum(r[3] for g in G for r in g["rows"])),
          open("ref_docx_data.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
