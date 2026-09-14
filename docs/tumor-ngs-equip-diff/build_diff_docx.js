const fs = require('fs');
const { VerticalMergeType, Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
        AlignmentType, BorderStyle, ShadingType, Footer, PageNumber, VerticalAlign,
        PageOrientation } = require('docx');
// 数据每次由 build_diff.py 现导，避免 Word 版落后于 HTML 版
require('child_process').execSync('python3 export_diff_data.py', { stdio: 'inherit' });
const D = JSON.parse(fs.readFileSync('diff_docx_data.json', 'utf8'));

const SONG = { ascii: 'Times New Roman', eastAsia: '宋体', hAnsi: 'Times New Roman' };
const HEI  = { ascii: 'Arial',           eastAsia: '黑体', hAnsi: 'Arial' };
const KAI  = { ascii: 'Times New Roman', eastAsia: '楷体', hAnsi: 'Times New Roman' };
const BODY = 21, TBL = 18, CW = 9860, IND = 420, LINE = 380;
const NONE  = { style: BorderStyle.NONE,   size: 0,  color: 'FFFFFF' };
const THICK = { style: BorderStyle.SINGLE, size: 12, color: '000000' };
const MED   = { style: BorderStyle.SINGLE, size: 6,  color: '000000' };
const HAIR  = { style: BorderStyle.SINGLE, size: 2,  color: 'BFBFBF' };

const run = (t, o = {}) => new TextRun({ text: t,
  font: o.hei ? HEI : (o.kai ? KAI : SONG), size: o.size || BODY,
  bold: !!o.bold, color: o.color || '000000', characterSpacing: o.cs || undefined });

// **加粗** 与 ＿＿ 填空（下划线空格）
function runs(text, o = {}) {
  const out = [];
  text.split(/(\*\*[^*]+\*\*|＿＿)/).filter(Boolean).forEach(seg => {
    if (seg === '＿＿') out.push(new TextRun({ text: '        ', underline: {}, font: o.kai ? KAI : SONG, size: o.size || BODY }));
    else if (seg.startsWith('**') && seg.endsWith('**')) out.push(run(seg.slice(2, -2), { ...o, bold: true }));
    else out.push(run(seg, o));
  });
  return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t, o),
  spacing: { line: LINE, after: o.after === undefined ? 100 : o.after },
  indent: { firstLine: o.noind ? 0 : IND, left: o.left || 0 },
  alignment: AlignmentType.BOTH });
const H2 = t => new Paragraph({ children: [run(t, { hei: true, bold: true, size: 25 })],
  spacing: { before: 320, after: 140, line: LINE }, keepNext: true });
const CAP = t => new Paragraph({ children: [run(t, { hei: true, bold: true, size: 20 })],
  spacing: { before: 140, after: 80 }, keepNext: true });
// 拟稿说明：楷体 + 左侧竖线 + 浅底
const DN = t => new Paragraph({ children: runs(t, { kai: true, size: 19 }),
  spacing: { before: 120, after: 160, line: 320 }, indent: { left: 340, firstLine: 0 },
  alignment: AlignmentType.BOTH,
  shading: { type: ShadingType.CLEAR, fill: 'F4F4F4', color: 'auto' },
  border: { left: { style: BorderStyle.SINGLE, size: 12, color: '808080', space: 10 } } });

const H3 = t => new Paragraph({ children: [run(t, { hei: true, bold: true, size: 22 })],
  spacing: { before: 220, after: 100, line: LINE }, keepNext: true });
function cell(text, w, o = {}) {
  const lines = Array.isArray(text) ? text : [text];
  return new TableCell({ width: { size: w, type: WidthType.DXA },
    borders: { top: o.top || NONE, bottom: o.bottom || HAIR, left: NONE, right: NONE },
    shading: o.shade ? { type: ShadingType.CLEAR, fill: o.shade, color: 'auto' } : undefined,
    columnSpan: o.span, verticalMerge: o.merge, verticalAlign: VerticalAlign.TOP,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: lines.map(t => new Paragraph({ children: runs(String(t), { size: TBL, hei: !!o.hei, bold: !!o.bold }),
      alignment: o.center ? AlignmentType.CENTER : (o.right ? AlignmentType.RIGHT : AlignmentType.LEFT),
      spacing: { line: 280 } })) });
}
const head = (cols, w) => new TableRow({ tableHeader: true,
  children: cols.map((c, i) => cell(c, w[i], { hei: true, bold: true, top: THICK, bottom: MED })) });
const table = (w, rows) => new Table({ columnWidths: w,
  width: { size: w.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  borders: { top: NONE, bottom: NONE, left: NONE, right: NONE, insideHorizontal: NONE, insideVertical: NONE },
  rows });


// 变更类别 → 底色 / 文字色
const C = {
  '新增': { bg: 'E6F4EA', fg: '1B7A3D', lab: '新增' },
  '调入': { bg: 'F1EAFA', fg: '6B3FA0', lab: '调入' },
  '修改': { bg: 'FDF2DC', fg: '9A6200', lab: '修改' },
  '未变': { bg: null,     fg: null,     lab: '—'   },
};
const DEL = { bg: 'FBEAEA', fg: 'A32020' };
const TODO = { bg: 'FFE9D6', fg: '8A4B00' };

// 多段落文字的单元格：segs = [{t, color, bold, size}]
function seg(list, w, o = {}) {
  return new TableCell({ width: { size: w, type: WidthType.DXA },
    borders: { top: o.top || NONE, bottom: o.bottom || HAIR, left: NONE, right: NONE },
    shading: o.shade ? { type: ShadingType.CLEAR, fill: o.shade, color: 'auto' } : undefined,
    columnSpan: o.span, verticalAlign: VerticalAlign.TOP,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: list.map(ps => new Paragraph({
      children: ps.map(s => new TextRun({ text: s.t, font: s.hei ? HEI : SONG,
        size: s.size || TBL, bold: !!s.bold, color: s.color || '000000',
        strike: !!s.strike })),
      alignment: o.center ? AlignmentType.CENTER : AlignmentType.LEFT,
      spacing: { line: 280 } })) });
}

const k = [];
k.push(new Paragraph({ children: [run('苏州市立医院分子诊断中心', { hei: true, size: 24, cs: 60 })],
  alignment: AlignmentType.CENTER, spacing: { after: 160 } }));
k.push(new Paragraph({ children: [run('肿瘤 NGS 平台设备清单　变更对照', { bold: true, size: 40, cs: 20 })],
  alignment: AlignmentType.CENTER, spacing: { after: 100, line: 440 } }));
k.push(new Paragraph({ children: [run('底稿：9.12 版（szwzf）　·　本稿：9.13 版（郭鹏达）', { size: 21, color: '444444' })],
  alignment: AlignmentType.CENTER, spacing: { after: 260 },
  border: { bottom: { style: BorderStyle.DOUBLE, size: 6, color: '000000', space: 10 } } }));

k.push(H2('一、分区结构的变化'));
k.push(P('9.13 版把分区由 **8 间调整为 9 间**，核心是三件事：**破碎区并入文库制备区**、**扩增拆成一区与二区**、**电泳单独成间**。'));
const WA = [2700, 2700, 4460];
const SUM = [
 ['试剂准备间', '试剂准备间', '未变'],
 ['PCR2 样本制备区（组织）', 'PCR2 样本制备区（组织）', '未变'],
 ['PCR3 样本制备区（血浆）', 'PCR3 样本制备区（血浆）', '未变'],
 ['PCR4 破碎区\nPCR5 文库制备区', 'PCR4 文库制备区', '两间合并：核酸片段化＋末端修复＋接头连接＋文库构建同区完成'],
 ['—', 'PCR5 扩增一区', '原 PCR5 腾出，改作文库预扩增'],
 ['PCR6 杂交捕获区', 'PCR6 杂交捕获区', '步骤增加「纯化」'],
 ['PCR7 扩增区（捕获后扩增＋上机前质检）', 'PCR7 扩增二区（捕获后扩增）', '上机前质检移出'],
 ['PCR8 测序区', 'PCR8 测序区', '未变'],
 ['—', 'PCR9 电泳', '新增分区，承接原 PCR7 的上机前质检'],
];
k.push(table(WA, [ head(['9.12 版（8 间）', '9.13 版（9 间）', '说明'], WA),
  ...SUM.map((r, i) => { const b = i === SUM.length - 1 ? THICK : HAIR;
    const chg = ['PCR4 文库制备区','PCR5 扩增一区','PCR7 扩增二区（捕获后扩增）','PCR9 电泳'].includes(r[1]);
    return new TableRow({ children: [
      seg(r[0].split('\n').map(x => [{ t: x }]), WA[0], { bottom: b }),
      seg(r[1].split('\n').map(x => [{ t: x, bold: chg }]), WA[1], { bottom: b }),
      seg([[{ t: r[2] }]], WA[2], { bottom: b })] }); }) ]));
k.push(P('规模：**60 行／104 台（件）　→　70 行／106 台（件）**。净增 10 行、2 台（件）。'));

k.push(H2('二、逐行对照'));
k.push(P('底色含义：绿＝**新增**（全院总数增加，需增配），紫＝**调入**（全院总数未变，只换了分区），黄＝参数或数量修改（表内注明原值），红＝移出本区，无底色＝未变。「待补」标记表示厂商与型号尚未填写。', { size: 19 }));

const W = [2300, 1500, 2560, 560, 1700, 1240];
const eq = [head(['产品名称', '建议厂商', '建议规格型号', '数量', '用途', '变更'], W)];
D.groups.forEach((g, gi) => {
  // 分区标题行
  const hd = [[{ t: g.room, hei: true, bold: true, size: 19 }, { t: '　' + g.step, size: 18, color: '555555' }]];
  const marks = [];
  if (g.room_new) marks.push({ t: '　新增分区', hei: true, size: 17, color: C['新增'].fg, bold: true });
  if (g.room_old) marks.push({ t: '　改名 ', hei: true, size: 17, color: C['修改'].fg, bold: true },
                              { t: g.room_old, size: 17, color: '555555', strike: true });
  if (g.step_old) marks.push({ t: '　步骤 ', hei: true, size: 17, color: C['修改'].fg, bold: true },
                              { t: g.step_old, size: 17, color: '555555', strike: true });
  if (marks.length) hd[0].push(...marks);
  if (g.note) hd.push([{ t: g.note, size: 17, color: '555555' }]);
  eq.push(new TableRow({ children: [seg(hd, W.reduce((a, b2) => a + b2, 0), { span: 6, shade: 'F2F2F2', bottom: HAIR })] }));

  g.rows.forEach(r => {
    const c = C[r.tag];
    const name = [{ t: r.dev }];
    if (c.fg) name.push({ t: '　' + c.lab, hei: true, size: 17, color: c.fg, bold: true });
    if (r.todo) name.push({ t: '　待补', hei: true, size: 17, color: TODO.fg, bold: true });
    const mod = [[{ t: r.mod }]];
    if (r.old) mod.push([{ t: '原：' + r.old, size: 17, color: C['修改'].fg }]);
    if (r.gtot) mod.push([{ t: r.gtot, size: 17, color: '555555' }]);
    const o = { bottom: HAIR, shade: c.bg };
    eq.push(new TableRow({ children: [
      seg([name], W[0], o), seg([[{ t: r.ven }]], W[1], o), seg(mod, W[2], o),
      seg([[{ t: r.qty }]], W[3], { ...o, center: true }),
      seg([[{ t: r.use }]], W[4], o),
      seg([[{ t: c.lab, color: c.fg || undefined, hei: !!c.fg, bold: !!c.fg }]], W[5], { ...o, center: true })] }));
  });

  g.gone.forEach(x => {
    eq.push(new TableRow({ children: [seg([[
      { t: x.dev, strike: true, color: '555555' },
      { t: '　移出　', hei: true, size: 17, color: DEL.fg, bold: true },
      { t: x.to, size: 18, color: DEL.fg }]], W.reduce((a, b2) => a + b2, 0),
      { span: 6, shade: DEL.bg, bottom: HAIR })] }));
  });
});
k.push(table(W, eq));

k.push(H2('三、全院台件数的变化'));
k.push(P('「调入」与「新增」的分界在这张表：**全院合计没变的是换了分区，合计增加的才需要增配**。净差额只有 +2 台（件），但那是移液器减 8 支抵掉的结果——真正增加的是仪器。'));
const WQ = [1800, 720, 720, 700, 2960, 2960];
k.push(table(WQ, [ head(['设备', '9.12', '9.13', '差额', '9.12 分布', '9.13 分布'], WQ),
  ...D.qty.map((m, i) => { const b = i === D.qty.length - 1 ? THICK : HAIR;
    const c = m.d > 0 ? C['新增'] : { bg: DEL.bg, fg: DEL.fg };
    const o = { bottom: b, shade: c.bg };
    return new TableRow({ children: [
      seg([[{ t: m.dev }]], WQ[0], o),
      seg([[{ t: String(m.old) }]], WQ[1], { ...o, center: true }),
      seg([[{ t: String(m.new), bold: true }]], WQ[2], { ...o, center: true }),
      seg([[{ t: (m.d > 0 ? '+' : '') + m.d, bold: true, color: c.fg }]], WQ[3], { ...o, center: true }),
      seg([[{ t: m.sby, size: 17, color: '555555' }]], WQ[4], o),
      seg([[{ t: m.gby, size: 17, color: '555555' }]], WQ[5], o)] }); }) ]));

k.push(H2('四、待补项：厂商与规格型号为空'));
k.push(P('9.13 版新拉出的行有 8 行未填厂商与型号，集中在 PCR4 与 PCR5。这些设备在 9.12 版中均有取值，右两列为建议回填值。'));
const WT = [2200, 2200, 620, 2100, 2740];
k.push(table(WT, [ head(['分区', '产品名称', '数量', '建议厂商（据 9.12）', '建议规格型号（据 9.12）'], WT),
  ...D.todos.map((x, i) => { const b = i === D.todos.length - 1 ? THICK : HAIR;
    const o = { bottom: b, shade: TODO.bg };
    return new TableRow({ children: [
      seg([[{ t: x.room }]], WT[0], o), seg([[{ t: x.dev }]], WT[1], o),
      seg([[{ t: x.qty }]], WT[2], { ...o, center: true }),
      seg([[{ t: x.ven }]], WT[3], o), seg([[{ t: x.mod }]], WT[4], o)] }); }) ]));
k.push(P('另：PCR4 的生物安全柜（A2 型）用途列为空；PCR6 与 PCR7 表内各有一整行空行，本对照稿已跳过，故行数按 70 行计。', { size: 19 }));

k.push(new Paragraph({ children: [run('苏州市立医院分子诊断中心', { hei: true, bold: true })],
  alignment: AlignmentType.RIGHT, spacing: { before: 400, line: LINE }, indent: { right: 400 } }));
k.push(new Paragraph({ children: [run('二〇二六年九月十四日')],
  alignment: AlignmentType.RIGHT, spacing: { line: LINE }, indent: { right: 400 } }));

const doc = new Document({
  styles: { default: { document: { run: { font: SONG, size: BODY }, paragraph: { spacing: { line: LINE } } } } },
  sections: [{
    properties: { page: { size: { orientation: PageOrientation.PORTRAIT },
                          margin: { top: 1134, bottom: 1021, left: 1021, right: 1021 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [run('— '), new TextRun({ children: [PageNumber.CURRENT], font: SONG, size: 19 }), run(' —')] })] }) },
    children: k,
  }],
});
Packer.toBuffer(doc).then(b => {
  fs.writeFileSync('苏州市立医院-肿瘤NGS设备清单变更对照（9.13 vs 9.12）.docx', b);
  console.log('已生成 docx:', (b.length / 1024).toFixed(0), 'KB');
});
