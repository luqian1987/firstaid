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
  ['本项目使用太湖新城总院区病理科现有 PCR 多分区实验室。中标方负责设备进场前的现场勘察，就台面承重、供电、给排水、温湿度与网络接入等提出书面要求，并配合院方完成设备就位前的条件准备，直至各功能分区满足临床项目开展的场地要求。',
   '**实验室场地的改造与建设不属于本项目采购范围**，包括现阶段病理科实验室的局部改造（如测序室边台改造为承重桌等）与后续分子诊断中心的场地建设，**均由院方组织实施并承担相应费用，不计入本项目报价**；中标方负责提出相应的技术条件要求并配合实施。']],
 ['2　负责平台配套设备、试剂的供应',
  '附件一所列设备与器具**由中标方全部投入**。试剂按院方确定的拟开展检测项目供应，每一癌种可包含多个检测项目及多个试剂盒，**全程冷链配送至太湖新城总院实验室**，服务期内持续稳定供应；其中**承担临床检测功能的核心试剂盒，须取得国家药品监督管理局第三类医疗器械注册证，注册证在有效期内，注册适用范围覆盖对应癌种，且注册证载明的适用机型包含 MGISEQ-2000**；文库构建等环节所用的通用耗材与辅助试剂，按实验需要配套供应。设备、试剂供应以满足实验室项目开展的需求为标准。'],
 ['3　负责质量管理体系建设，协助室间质评',
  '负责平台检测项目的标准化操作文件及实验室其他质量管理体系文件的建立；配合完成方法学性能验证（精密度、正确度、**最低检出变异频率、测序深度与覆盖均一度**、可报告范围等），**性能验证在院方指定的场地与设备上进行，验证结论由院方确认，未通过验证的产品予以更换**；协助完成并上报室间质评结果；配合院方通过临床基因扩增检验实验室技术审核。'],
 ['4　负责 NGS 项目技术转移与驻场支持',
  '负责人员带教与标准化流程输出，内容覆盖样本前处理、文库构建、杂交捕获、上机测序、数据分析与报告解读全流程，培训形成书面记录与考核结论。'],
 ['5　负责临床沟通与报告解读支持',
  '提供检测项目的临床沟通与疑难病例报告解读支持；配合院方面向肿瘤科、呼吸科、胸外科、消化外科、乳腺外科、病理科等相关科室开展技术交流。'],
 ['6　负责项目推广',
  '有专人负责区域业务拓展与临床科室对接，配合院方开展本平台检测项目的临床宣讲与 MDT 沟通，提升平台的临床应用与检测量。'],
 ['7　负责数据安全与本地化部署',
  '分析解读软硬件在院内本地化部署。**本平台产生的检测数据归院方所有，存储于院内，不上传至院外，不出境**；涉及人类遗传资源的活动，符合《中华人民共和国人类遗传资源管理条例》及其实施细则的规定。']
].forEach(([h, t]) => { k.push(H3(h)); (Array.isArray(t) ? t : [t]).forEach(x => k.push(P(x))); });

k.push(H2('人员规划'));
k.push(P('**中标方配备技术人员 1–2 名**，具备分子诊断或临床检验相关背景并持临床基因扩增检验实验室技术人员上岗证，负责带教、技术对接与日常运行配合。**驻场人数按院方实际需求与样本量调整**，待院方人员具备独立操作能力后转为定期回访与按需响应。'));
k.push(P('院方按拟开展项目与预估样本量测算所需检验人员数量并负责招聘，**相关人员待遇由中标方承担**。中标方人员进入实验室遵守院方生物安全、感染控制与信息安全的相关规定并签署保密承诺；检验报告由院方具备相应资质的人员审核签发。'));

k.push(H2('科研支持'));
k.push(P('**本项目不设科研绑定条款**，不以科研合作、驻场科研人员、课题与文章署名、学术会议或外出考察等名义，附加与本项目采购相挂钩的条件。'));
k.push(P('按院方实际需要，提供本平台检测数据的技术性梳理、方法学资料与生物信息分析支持；如院方另有科研合作意向，另行立项、单独签署协议，与本次采购不作关联。'));

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
