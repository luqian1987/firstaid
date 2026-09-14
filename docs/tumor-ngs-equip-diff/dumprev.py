# -*- coding: utf-8 -*-
"""带修订（tracked changes）感知的 docx 表格提取：mode='final' 接受全部修订，'orig' 拒绝全部修订"""
import zipfile,re,html
def _cell_text(tc, mode):
    s=tc
    if mode=="final":
        s=re.sub(r"<w:del\b.*?</w:del>","",s,flags=re.S)          # 删除的内容不出现在终稿
    else:
        s=re.sub(r"<w:ins\b.*?</w:ins>","",s,flags=re.S)          # 插入的内容不出现在原稿
        s=re.sub(r"<w:delText(\s[^>]*)?>", r"<w:t\1>", s).replace("</w:delText>","</w:t>")
    s=re.sub(r"<w:br[^>]*/>"," ",s)
    return html.unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", s, re.S))).strip()

def rows(path, mode="final"):
    x=zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    out=[]
    for tbl in re.finditer(r"<w:tbl>.*?</w:tbl>", x, re.S):
        for tr in re.finditer(r"<w:tr\b.*?</w:tr>", tbl.group(0), re.S):
            s=tr.group(0)
            pr=re.search(r"<w:trPr>.*?</w:trPr>", s, re.S)
            pr=pr.group(0) if pr else ""
            ins_row="<w:ins " in pr or "<w:ins/" in pr
            del_row="<w:del " in pr or "<w:del/" in pr
            if mode=="final" and del_row: continue      # 整行被删
            if mode=="orig"  and ins_row: continue      # 整行是新增
            cells=[_cell_text(c,mode) for c in re.findall(r"<w:tc>.*?</w:tc>", s, re.S)]
            out.append(((cells+[""]*7)[:7], ins_row, del_row))
    return out

def norm(rs):
    """补齐纵向合并的房间/步骤列"""
    out=[]; room=step=""
    for cells,ins,dl in rs:
        if cells[0]=="房间": continue
        if cells[0]: room=cells[0]
        if cells[1]: step=cells[1]
        out.append((room, step, cells[2], cells[3], cells[4], cells[5], cells[6], ins, dl))
    return out
