# -*- coding: utf-8 -*-
"""从 OLE2 .doc 的 WordDocument 流中提取正文（FIB → CLX → 分片解码）"""
import olefile, struct, sys
f=olefile.OleFileIO(sys.argv[1])
wd=f.openstream('WordDocument').read()
# FIB
fibbase_fWhichTblStm=(struct.unpack_from('<H',wd,0x0A)[0]>>9)&1
tbl='1Table' if fibbase_fWhichTblStm else '0Table'
tb=f.openstream(tbl).read()
fcClx=struct.unpack_from('<i',wd,0x01A2)[0]
lcbClx=struct.unpack_from('<I',wd,0x01A6)[0]
clx=tb[fcClx:fcClx+lcbClx]
# 跳过 Prc
i=0
while i<len(clx) and clx[i]==0x01:
    cb=struct.unpack_from('<h',clx,i+1)[0]; i+=3+cb
assert clx[i]==0x02, "未找到 Pcdt"
lcbPlcfPcd=struct.unpack_from('<I',clx,i+1)[0]
plc=clx[i+5:i+5+lcbPlcfPcd]
n=(len(plc)-4)//12                       # CP 数 = n+1，PCD 各 8 字节
cps=[struct.unpack_from('<I',plc,4*k)[0] for k in range(n+1)]
out=[]
for k in range(n):
    pcd=plc[4*(n+1)+8*k : 4*(n+1)+8*k+8]
    fc=struct.unpack_from('<I',pcd,2)[0]
    comp=(fc>>30)&1                       # 1 = 单字节 CP1252/GBK
    fc=fc&0x3FFFFFFF
    ln=cps[k+1]-cps[k]
    if comp:
        raw=wd[fc//2 : fc//2+ln]
        out.append(raw.decode('cp936','replace'))
    else:
        raw=wd[fc : fc+ln*2]
        out.append(raw.decode('utf-16-le','replace'))
txt="".join(out)
for a,b in (('\r','\n'),('\x07','\t│\t'),('\x0b','\n'),('\x0c','\n──分页──\n'),
            ('\x01','[图]'),('\x02',''),('\x08',''),('\x13',''),('\x14',''),('\x15','')):
    txt=txt.replace(a,b)
print(txt)
