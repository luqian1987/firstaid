const fs = require('fs');
const { VerticalMergeType, Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
        AlignmentType, BorderStyle, ShadingType, Footer, PageNumber, VerticalAlign,
        PageOrientation } = require('docx');
// 数据每次由 build_ref.py 现导，避免 Word 版落后于 HTML 版
require('child_process').execSync('python3 export_ref_data.py', { stdio: 'inherit' });
const D = JSON.parse(fs.readFileSync('ref_docx_data.json', 'utf8'));

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

const k = [];
k.push(new Paragraph({ children: [run('苏州市立医院分子诊断中心', { hei: true, size: 24, cs: 60 })],
  alignment: AlignmentType.CENTER, spacing: { after: 160 } }));
k.push(new Paragraph({ children: [run('肿瘤 NGS 平台招标需求', { bold: true, size: 44, cs: 20 })],
  alignment: AlignmentType.CENTER, spacing: { after: 100, line: 440 } }));
k.push(new Paragraph({ children: [run('建设地点：太湖新城总院区', { size: 21, color: '444444' })],
  alignment: AlignmentType.CENTER, spacing: { after: 260 },
  border: { bottom: { style: BorderStyle.DOUBLE, size: 6, color: '000000', space: 10 } } }));

k.push(H2('测序仪'));
const W1 = [900, 2200, 5160, 1600];
k.push(table(W1, [ head(['序号', '品牌', '型号', '数量（台）'], W1),
  new TableRow({ children: [cell('1', W1[0], { center: true, bottom: THICK }),
    cell('华大智造', W1[1], { bottom: THICK }), cell('MGISEQ-2000', W1[2], { bottom: THICK }),
    cell('1', W1[3], { center: true, bottom: THICK })] }) ]));

k.push(H2('服务内容'));
[['1　负责实验室场地适配',
  ['本项目现阶段使用现有 PCR 多分区实验室。中标方负责设备进场前的现场勘察，就场地承重、供电、温湿度与网络接入等条件提出书面要求，并配合院方完成设备就位前的条件准备，直至各功能分区满足临床项目开展的场地要求。',
   '**现阶段实验室的局部改造**（如测序室边台改造为承重桌等）**由中标方负责实施**；**后续分子诊断中心的场地建设由院方组织实施并承担相应费用**，中标方配合完成功能分区与设备布局的规划。']],
 ['2　负责平台配套设备、试剂的供应',
  '附件一所列设备与器具**由中标方全部投入**。试剂按院方确定的拟开展检测项目配套供应，**全程冷链配送，服务期内持续稳定供应**；其中**承担临床检测功能的核心试剂盒，须取得国家药品监督管理局第三类医疗器械注册证，注册适用范围覆盖对应癌种**。'],
 ['3　负责质量管理体系建设，协助室间质评',
  '负责平台检测项目的标准化操作文件及实验室其他质量管理体系文件的建立；配合完成方法学性能验证，**性能验证在院方指定的场地与设备上进行，验证结论由院方确认，未通过验证的产品予以更换**；协助完成并上报室间质评结果；配合院方通过临床基因扩增检验实验室技术审核。'],
 ['4　负责 NGS 项目技术转移与驻场支持',
  '负责人员带教与标准化流程输出，内容覆盖实验操作、上机测序、数据分析与报告解读全流程，培训形成书面记录与考核结论。'],
 ['5　负责临床沟通与报告解读支持',
  '提供检测项目的临床沟通与疑难病例报告解读支持；配合院方面向相关临床科室开展技术交流。'],
 ['6　负责项目推广',
  '有专人负责临床科室对接，配合院方开展本平台检测项目的临床宣讲与 MDT 沟通，提升平台的临床应用与检测量。'],
 ['7　负责数据安全与本地化部署',
  '分析解读软硬件在院内本地化部署。**本平台产生的检测数据归院方所有，存储于院内，不上传至院外**；涉及人类遗传资源的活动，符合《中华人民共和国人类遗传资源管理条例》及其实施细则的规定。']
].forEach(([h, t]) => { k.push(H3(h)); (Array.isArray(t) ? t : [t]).forEach(x => k.push(P(x))); });

k.push(H2('人员规划'));
k.push(P('**中标方配备技术人员 1–2 名**，应具备分子诊断或临床检验相关专业背景，**持临床基因扩增检验实验室技术人员上岗证（PCR 上岗证）**，**具有高通量测序湿实验操作经验者优先**；负责带教、技术对接与日常运行配合。'));
k.push(P('院方招聘具备分子诊断或临床检验相关背景的人员，按拟开展项目与预估样本量测算，前期拟定 1–2 人，**相关人员待遇由中标方承担**。中标方人员进入实验室遵守院方生物安全、感染控制与信息安全的相关规定并签署保密承诺；检验报告由院方具备相应资质的人员审核签发。'));

k.push(H2('科研支持'));
k.push(P('中标方应具备检测数据的技术性梳理、方法学资料提供及生物信息分析支持能力，按院方实际需要配合开展，保障检测质量与结果解读的规范性。'));
k.push(P('随着平台数据积累，院方如提出数据分析、质量评价等进一步技术需求，中标方应在合规范围内予以配合。'));

k.push(H2('负责应急事件对接和处理'));
k.push(P('紧急情况下（不限于下表所列情况），负责或协助解决问题，保障报告发出的时效性和准确性，保证服务质量。'));
const W2 = [2400, 7460];
k.push(table(W2, [ head(['应急事件（举例）', '处理方案'], W2),
  ...D.emerg.map(([a, b2], i) => { const b = i === D.emerg.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [cell(a, W2[0], { bottom: b }), cell(b2, W2[1], { bottom: b })] }); }) ]));

k.push(H2('报价'));
const W3 = [2100, 3200, 4560];
k.push(table(W3, [ head(['公司', '报价', '备注'], W3),
  ...D.bid.map(([a, b2, c2]) => new TableRow({ children: [
    cell(a, W3[0], { bottom: THICK }), cell(b2, W3[1], { bottom: THICK }), cell(c2, W3[2], { bottom: THICK })] })) ]));

k.push(H2('附件一：设备清单'));
k.push(P('本清单共 ' + D.total + ' 项、' + D.qty + ' 台（件），**由中标方全部投入**，按房间与步骤列明。厂商与规格型号为建议配置，可结合院方使用习惯调整。'));
const W5 = [1080, 1340, 1580, 1340, 1900, 560, 2060];
const eq = [head(['房间', '步骤', '产品名称', '建议厂商\n（供参考）', '建议规格型号\n（供参考）', '数量', '用途'], W5)];
D.groups.forEach((g, gi) => {
  const label = g.room === g.zone.replace(/区$/, '间') ? [g.room] : [g.room, g.zone];
  g.rows.forEach((r, ri) => {
    const last = gi === D.groups.length - 1 && ri === g.rows.length - 1;
    const b = last ? THICK : HAIR;
    // 房间与步骤两列纵向合并，对齐参照文档的表结构
    const merge = ri === 0 ? VerticalMergeType.RESTART : VerticalMergeType.CONTINUE;
    eq.push(new TableRow({ children: [
      cell(ri === 0 ? label : '', W5[0], { bottom: b, merge }),
      cell(ri === 0 ? g.step : '', W5[1], { bottom: b, merge }),
      cell(r[0], W5[2], { bottom: b }), cell(r[1], W5[3], { bottom: b }), cell(r[2], W5[4], { bottom: b }),
      cell(String(r[3]), W5[5], { center: true, bottom: b }), cell(r[4], W5[6], { bottom: b }),
    ]}));
  });
});
k.push(table(W5, eq));

k.push(new Paragraph({ children: [run('苏州市立医院分子诊断中心', { hei: true, bold: true })],
  alignment: AlignmentType.RIGHT, spacing: { before: 400, line: LINE }, indent: { right: 400 } }));
k.push(new Paragraph({ children: [run('二〇二六年九月十一日')],
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
  fs.writeFileSync('苏州市立医院-肿瘤NGS平台招标需求（对院应答稿）.docx', b);
  console.log('已生成 docx:', (b.length / 1024).toFixed(0), 'KB');
});
