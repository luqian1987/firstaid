const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, BorderStyle, ShadingType, HeadingLevel,
  Footer, PageNumber, VerticalAlign, PageOrientation,
} = require('docx');

const D = JSON.parse(fs.readFileSync('report_data.json', 'utf8'));

/* ---------- 版式常量 ---------- */
const SONG = { ascii: 'Times New Roman', eastAsia: '宋体', hAnsi: 'Times New Roman' };
const HEI  = { ascii: 'Arial',           eastAsia: '黑体', hAnsi: 'Arial' };
const BODY = 21;      // 半磅 → 10.5pt 五号
const TBL  = 18;      // 9pt
const CW   = 9860;    // 正文净宽（DXA）
const IND  = 420;     // 首行缩进两字
const LINE = 380;     // 行距

const NONE  = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
const THICK = { style: BorderStyle.SINGLE, size: 12, color: '000000' };
const MED   = { style: BorderStyle.SINGLE, size: 6,  color: '000000' };
const HAIR  = { style: BorderStyle.SINGLE, size: 2,  color: 'BFBFBF' };

/* ---------- 段落helpers ---------- */
const run = (text, o = {}) => new TextRun({
  text, font: o.hei ? HEI : SONG, size: o.size || BODY,
  bold: !!o.bold, color: o.color || '000000',
  characterSpacing: o.cs || undefined,
});

// 支持 **加粗** 行内标记
function runs(text, o = {}) {
  return text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map(seg =>
    seg.startsWith('**') && seg.endsWith('**')
      ? run(seg.slice(2, -2), { ...o, bold: true })
      : run(seg, o));
}

const body = (text) => new Paragraph({
  children: runs(text),
  spacing: { line: LINE, after: 100 },
  indent: { firstLine: IND },
  alignment: AlignmentType.BOTH,
});

const h2 = (text) => new Paragraph({
  children: [run(text, { hei: true, bold: true, size: 25 })],
  spacing: { before: 320, after: 140, line: LINE },
  keepNext: true,
});

const h3 = (text) => new Paragraph({
  children: [run(text, { hei: true, bold: true, size: 22 })],
  spacing: { before: 200, after: 110, line: LINE },
  keepNext: true,
});

const caption = (text) => new Paragraph({
  children: [run(text, { hei: true, bold: true, size: 20 })],
  spacing: { before: 140, after: 80 },
  keepNext: true,
});

const note = (text) => new Paragraph({
  children: runs(text, { size: 19 }),
  spacing: { before: 90, after: 120, line: 320 },
  indent: { firstLine: 380 },
  alignment: AlignmentType.BOTH,
});

/* ---------- 表格 helpers ---------- */
function cell(text, w, o = {}) {
  const al = o.center ? AlignmentType.CENTER : (o.right ? AlignmentType.RIGHT : AlignmentType.LEFT);
  const lines = Array.isArray(text) ? text : [text];
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: {
      top: o.top || NONE, bottom: o.bottom || HAIR, left: NONE, right: NONE,
    },
    shading: o.shade ? { type: ShadingType.CLEAR, fill: o.shade, color: 'auto' } : undefined,
    columnSpan: o.span,
    verticalAlign: VerticalAlign.TOP,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: lines.map(t => new Paragraph({
      children: runs(String(t), { size: TBL, hei: !!o.hei, bold: !!o.bold }),
      alignment: al, spacing: { line: 280 },
    })),
  });
}

function head(cols, widths) {
  return new TableRow({
    tableHeader: true,
    children: cols.map((c, i) =>
      cell(c, widths[i], { hei: true, bold: true, top: THICK, bottom: MED })),
  });
}

function table(widths, rows) {
  return new Table({
    columnWidths: widths,
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    borders: { top: NONE, bottom: NONE, left: NONE, right: NONE,
               insideHorizontal: NONE, insideVertical: NONE },
    rows,
  });
}

// 末行加粗下框线，构成三线表
function closeLast(rows, widths, build) {
  const last = rows.length - 1;
  return rows.map((r, i) => build(r, i === last));
}

/* ---------- 文档内容 ---------- */
const kids = [];

kids.push(new Paragraph({
  children: [run('苏州市立医院分子诊断中心', { hei: true, size: 24, cs: 60 })],
  alignment: AlignmentType.CENTER, spacing: { after: 160 },
}));
kids.push(new Paragraph({
  children: [run('肿瘤 NGS 板块方案阶段性汇报', { bold: true, size: 44, cs: 20 })],
  alignment: AlignmentType.CENTER, spacing: { after: 100, line: 440 },
}));
kids.push(new Paragraph({
  children: [run('现阶段调研方向：太湖总院病理科现有 PCR 多分区实验室', { size: 21, color: '444444' })],
  alignment: AlignmentType.CENTER, spacing: { after: 200 },
  border: { bottom: { style: BorderStyle.DOUBLE, size: 6, color: '000000', space: 10 } },
}));

const META = [['汇 报 方', '华大基因'], ['汇报对象', '苏州市立医院各上级职能部门'],
              ['场　　地', '太湖总院病理科现有 PCR 多分区实验室'], ['日　　期', '2026 年 9 月 9 日']];
kids.push(new Paragraph({ text: '', spacing: { after: 120 } }));
kids.push(table([1500, 8360], META.map(([k, v], i) => new TableRow({
  children: [
    cell(k, 1500, { hei: true, bottom: NONE }),
    cell(v, 8360, { bottom: i === META.length - 1 ? MED : NONE }),
  ],
}))));
kids.push(new Paragraph({ text: '', spacing: { after: 200 } }));

kids.push(body('根据前期多部门沟通意见与现场实地考察情况，现就分子诊断中心肿瘤 NGS 板块的分区落位、设备配置及可开展检测项目形成阶段性汇报如下，请各位领导及相关职能部门审阅并给予指导意见。'));

/* 一 */
kids.push(h2('一、场地与分区情况'));
kids.push(h3('（一）总体情况'));
kids.push(body('本次调研场地为太湖总院病理科现有 PCR 多分区实验室。经现场勘察，该实验室共六个功能间，沿同一条走廊一字排开，每间均设独立缓冲间，人员经缓冲间进出。房间的物理顺序与肿瘤 NGS 检测的工艺流程方向完全一致，具备单向流条件。**六间房及各自缓冲间均已建成，本次不涉及新建与装修改造，仅作功能分配与设备进场。**'));
kids.push(body('工艺流程自上游至下游依次为：试剂准备区（试剂准备间）→ 标本与文库制备区（PCR2）→ 血浆文库制备区（PCR3）→ 杂交捕获区（PCR4）→ 文库扩增与检测区（PCR5）→ 测序区（PCR8）。标本与文库沿此方向单向传递，人员不逆向返回上游。其中 PCR5 与 PCR8 之间尚有 PCR6、PCR7 两间，本次不予占用。'));

kids.push(h3('（二）各功能间职能与现有条件'));
kids.push(caption('表 1　六个功能间的职能划分与现有条件核验'));
const W1 = [700, 1900, 3200, 3160, 900];
kids.push(table(W1, [
  head(['序号', '功能分区（房间）', '主要工作内容', '现有条件核验', '设备'], W1),
  ...closeLast(D.rooms, W1, (R, last) => {
    const b = last ? THICK : HAIR;
    return new TableRow({ children: [
      cell(String(D.rooms.indexOf(R) + 1), W1[0], { center: true, bottom: b }),
      cell([R.zone, '（' + R.room + '）'], W1[1], { bottom: b }),
      cell(R.work, W1[2], { bottom: b }),
      cell(R.cond, W1[3], { bottom: b }),
      cell(R.n + ' 项', W1[4], { center: true, bottom: b }),
    ]});
  }),
]));
kids.push(note('注：表中「设备」为该功能间应配置的设备与器具项数，明细见第二部分。'));

/* 二 */
kids.push(h2('二、设备配置清单'));
kids.push(h3('（一）配置原则'));
kids.push(body('本清单按六个功能分区列明设备与器具配置，作为配置比对与补齐的依据。**实验室现有设备经核验符合参数要求的予以沿用，缺配部分按本清单补齐**；在满足参数要求的前提下，具体品牌与型号可结合实验室现行使用习惯另行商定，不以本清单所列型号为限。'));
kids.push(body('本清单共 91 项，为设备与器具配置，试剂耗材清单另行出具。清单中同型号移液器已按功能间合并列示，产品编码完整保留；另有物料编码（EQP 及 1000 系列）在原始清单中一一对应，采购时可一并提供。'));
kids.push(h3('（二）分区配置明细'));
kids.push(caption('表 2　设备与器具配置明细（按功能间分组，共 91 项）'));
const W2 = [1900, 3300, 1800, 2060, 800];
const eqRows = [head(['产品编码', '产品名称', '设备名称', '参数要求', '数量'], W2)];
D.equip.forEach((g, gi) => {
  eqRows.push(new TableRow({ children: [
    cell(`${g.room}　${g.zone}　（${g.kinds} 项 / ${g.qty} 台件）`, CW,
         { span: 5, hei: true, bold: true, shade: 'F0F0F0', bottom: HAIR }),
  ]}));
  g.rows.forEach((r, ri) => {
    const last = gi === D.equip.length - 1 && ri === g.rows.length - 1;
    const b = last ? THICK : HAIR;
    eqRows.push(new TableRow({ children: [
      cell(r[0], W2[0], { bottom: b }), cell(r[1], W2[1], { bottom: b }),
      cell(r[2], W2[2], { bottom: b }), cell(r[3], W2[3], { bottom: b }),
      cell(String(r[4]), W2[4], { center: true, bottom: b }),
    ]}));
  });
});
kids.push(table(W2, eqRows));

/* 三 */
kids.push(h2('三、可开展检测项目与收费'));
kids.push(h3('（一）已明确物价的检测项目'));
kids.push(body('下列五个试剂盒均已取得国家药品监督管理局第三类医疗器械注册证，属已注册体外诊断试剂路径，非实验室自建项目（LDT），报批与合规风险相对较低。五项共用收费编码 012100000200000「高通量测序法检测费（病理样本）」，价格已在物价目录内。'));
kids.push(caption('表 3　已明确物价的可开展检测项目'));
const W3 = [600, 3000, 1700, 1200, 2160, 1200];
kids.push(table(W3, [
  head(['序号', '试剂盒名称 / 生产厂家', '注册证编号', '注册适用范围', '可拓展适用范围', '物价收费'], W3),
  ...D.kits.map((k, i) => {
    const b = i === D.kits.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [
      cell(k.no, W3[0], { center: true, bottom: b }),
      cell([k.name, k.mfr], W3[1], { bottom: b }),
      cell(k.reg, W3[2], { bottom: b }),
      cell(k.scope, W3[3], { bottom: b }),
      cell(k.ext, W3[4], { bottom: b }),
      cell(k.price, W3[5], { right: true, bottom: b }),
    ]});
  }),
]));
kids.push(note('注：「可拓展适用范围」指注册证适应证之外、临床有实际需求的瘤种，开展前需按院内规定完成新增项目论证与备案。'));

kids.push(h3('（二）其他已注册可选试剂盒（参考）'));
kids.push(body('上表之外，国内已取得第三类注册证的同类产品尚有多个，可在同一平台上按临床需求扩充项目菜单。下列两项为 PARP 抑制剂的伴随诊断试剂，覆盖卵巢癌、乳腺癌与前列腺癌，**与上表以肺癌、结直肠癌为主的项目菜单互补，不重复**。'));
kids.push(caption('表 4　其他已注册可选试剂盒'));
const W4 = [1700, 2800, 1200, 4160];
kids.push(table(W4, [
  head(['注册证编号', '试剂盒名称 / 生产厂家', '注册适用范围', '说明'], W4),
  ...D.ref.map((r, i) => {
    const b = i === D.ref.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [
      cell(r.reg, W4[0], { bottom: b }),
      cell([r.name, r.mfr], W4[1], { bottom: b }),
      cell(r.scope, W4[2], { bottom: b }),
      cell(r.note, W4[3], { bottom: b }),
    ]});
  }),
]));
kids.push(note('注：上列产品名称、适用范围与伴随诊断药物已比对厂家公开信息，注册证编号建议以最新《医疗器械注册证》原件为准。此类产品的收费执行口径需另行确认，未包含在已明确物价的五项之内；实际引入前应完成新增项目论证与物价备案。'));

/* 四 */
kids.push(h2('四、NGS 临床应用方向'));
kids.push(body('本次项目落在实体瘤伴随诊断这一类。从平台角度看，实验室建成后所承载的能力不止于此。现按大类梳理国内 NGS 临床应用的主要方向，供分子诊断中心中长期规划参考。各方向的监管成熟度并不相同：**标注「已有注册产品」的可直接选用注册试剂盒开展，标注「多以 LDT 路径开展」的则需按自建项目管理**。'));
kids.push(caption('表 5　国内 NGS 临床应用方向（大类）'));
const W5 = [600, 2000, 5460, 1800];
kids.push(table(W5, [
  head(['序号', '应用方向', '主要内容', '开展路径'], W5),
  ...D.dirs.map((x, i) => {
    const b = i === D.dirs.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [
      cell(String(i + 1), W5[0], { center: true, bottom: b }),
      cell(x.t, W5[1], { bottom: b }),
      cell(x.d, W5[2], { bottom: b }),
      cell(x.st, W5[3], { bottom: b }),
    ]});
  }),
]));
kids.push(note('注：以上为应用方向的大类梳理，不构成项目承诺。各方向开展前均需完成新增项目论证、试剂盒选型与物价备案；跨方向共用同一测序平台时，还需确认各试剂盒注册证载明的适用机型。'));

/* 结语与落款 */
kids.push(new Paragraph({
  children: runs('以上汇报，请各位领导及相关职能部门审阅，并就分区落位方案、设备配置口径及项目开展次序给予进一步指导意见。'),
  spacing: { before: 280, after: 160, line: LINE },
  indent: { firstLine: IND }, alignment: AlignmentType.BOTH,
}));
kids.push(new Paragraph({
  children: [run('华大基因', { hei: true, bold: true })],
  alignment: AlignmentType.RIGHT, spacing: { before: 320, line: LINE },
  indent: { right: 400 },
}));
kids.push(new Paragraph({
  children: [run('二〇二六年九月九日')],
  alignment: AlignmentType.RIGHT, spacing: { line: LINE },
  indent: { right: 400 },
}));

/* ---------- 文档 ---------- */
const doc = new Document({
  styles: { default: { document: { run: { font: SONG, size: BODY }, paragraph: { spacing: { line: LINE } } } } },
  sections: [{
    properties: {
      page: {
        size: { orientation: PageOrientation.PORTRAIT },   // A4 为默认
        margin: { top: 1134, bottom: 1021, left: 1021, right: 1021 },  // 20mm / 18mm
      },
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [run('— '), new TextRun({ children: [PageNumber.CURRENT], font: SONG, size: 19 }), run(' —')],
      })] }),
    },
    children: kids,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('苏州市立医院-肿瘤NGS板块方案阶段性汇报.docx', buf);
  console.log('已生成 docx:', (buf.length / 1024).toFixed(0), 'KB');
});
