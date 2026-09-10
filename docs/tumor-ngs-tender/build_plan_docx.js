const fs = require('fs');
const { VerticalMergeType, Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
        AlignmentType, BorderStyle, ShadingType, Footer, PageNumber, VerticalAlign,
        PageOrientation } = require('docx');
// 数据每次由 build_tender.py 现导，避免 Word 版落后于 HTML 版
require('child_process').execSync('python3 export_plan_data.py', { stdio: 'inherit' });
const D = JSON.parse(fs.readFileSync('plan_docx_data.json', 'utf8'));

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
k.push(new Paragraph({ children: [run('肿瘤 NGS 平台建设需求', { bold: true, size: 44, cs: 20 })],
  alignment: AlignmentType.CENTER, spacing: { after: 100, line: 440 } }));
k.push(new Paragraph({ children: [run('建设地点：太湖新城总院区', { size: 21, color: '444444' })],
  alignment: AlignmentType.CENTER, spacing: { after: 260 },
  border: { bottom: { style: BorderStyle.DOUBLE, size: 6, color: '000000', space: 10 } } }));

k.push(P('本项目为**整体采购**：基因测序仪、配套设备与器具、拟开展检测项目所需的检测试剂及相应服务，由同一投标人整体投标，**不接受分包，不接受联合体投标；所投产品应为本国产品**。实验室已建成并具备功能分区，本次不涉及新建与装修改造，设备就位所需的台面承重等局部适配由中标人负责。服务期限自合同签订之日起 ＿＿ 年。'));

k.push(H2('测序仪'));
k.push(CAP('表 1　基因测序仪要求（不指定品牌与型号）'));
const W1 = [700, 1900, 7260];
k.push(table(W1, [ head(['序号', '项目', '要求'], W1),
  ...D.tech.map(([t, d], i) => { const b = i === D.tech.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [cell(String(i + 1), W1[0], { center: true, bottom: b }),
      cell(t, W1[1], { bottom: b }), cell(d, W1[2], { bottom: b })] }); }) ]));

k.push(H2('服务内容'));
[['1　负责平台设备与试剂的供应',
  '按附件一供应全部配套设备与器具，并供应拟开展检测项目所需的检测试剂。**设备与试剂应满足实验室开展临床检测的完整需要，投标人不得作缺项或以「院方自备」等方式排除。**'],
 ['2　负责设备进场、安装、调试与场地适配',
  '负责设备的运输、就位、安装与调试，直至各功能分区具备开展临床检测的条件。进场前完成现场勘察，就台面承重、供电、给排水、温湿度与网络接入等条件提出书面要求；**因设备就位需对既有实验台面及配套设施进行局部适配调整的，由中标人负责实施，费用计入报价。**'],
 ['3　负责质量管理体系建设，配合性能验证与室间质评',
  '配合建立本平台检测项目的标准操作规程及相关质量管理体系文件；配合完成方法学性能验证（精密度、正确度、检出限、可报告范围等）；协助院方参加室间质评并上报结果；配合院方通过临床基因扩增检验实验室技术审核。**所投试剂盒须通过院方组织的性能验证方可用于临床检测，验证结论由院方确认，未通过验证的产品应予更换。**'],
 ['4　负责 NGS 项目技术转移与人员培训',
  '对院方指定人员进行系统培训，内容覆盖样本前处理、文库构建、杂交捕获、上机测序、数据分析与报告解读全流程，**直至院方人员具备独立操作能力**。培训应形成书面记录与考核结论。'],
 ['5　负责临床沟通与报告解读支持',
  '提供检测项目的临床沟通、疑难病例报告解读的技术支持；配合院方开展面向临床科室的技术交流。'],
 ['6　负责售后维保与备件供应',
  '提供设备的日常维护、故障响应与备件供应。质保期限、故障响应与到场时限由双方在合同中约定；质保期满后的维保价格，投标人应在投标文件中一并报出。'],
 ['7　负责数据安全与本地化部署',
  '分析解读软硬件应支持院内本地化部署。**本平台产生的检测数据归院方所有，应存储于院内，不得上传至院外，不得出境**；涉及人类遗传资源的活动，应符合《中华人民共和国人类遗传资源管理条例》及其实施细则的规定。']
].forEach(([h, t]) => { k.push(H3(h)); k.push(P(t)); });

k.push(H2('人员规划'));
k.push(P('中标人应指定项目负责人一名，并**按项目实际需要配备具备分子诊断或临床检验相关背景的技术人员不少于 1 名，参与日常项目的技术对接、培训带教与运行配合**。其工作范围为技术支持与运行配合，检验报告由院方具备相应资质的人员审核签发。中标人人员进入实验室应遵守院方生物安全、感染控制与信息安全的相关规定，并签署保密承诺。培训完成并经院方考核合格后，驻场支持转为定期回访与按需响应。'));

k.push(H2('应急事件对接和处理'));
k.push(P('中标人应就下列情形制定应急预案并在合同中约定响应时限，保障检测报告的时效性与准确性。'));
k.push(CAP('表 2　应急事件与处理方案'));
const W2 = [2400, 7460];
k.push(table(W2, [ head(['应急事件', '处理方案'], W2),
  ...D.emerg.map(([a, b2], i) => { const b = i === D.emerg.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [cell(a, W2[0], { bottom: b }), cell(b2, W2[1], { bottom: b })] }); }) ]));

k.push(H2('拟开展检测项目'));
k.push(P('本平台首批拟开展下列癌种的检测项目。每一癌种可包含多个检测项目及多个试剂盒，具体清单由投标人在投标文件中逐项列明。**所投试剂盒须已取得国家药品监督管理局第三类医疗器械注册证，注册适用范围覆盖所对应的癌种，且注册证载明的适用机型包含所投基因测序仪机型。**'));
k.push(CAP('表 3　首批拟开展检测项目'));
const W3 = [700, 2000, 7160];
k.push(table(W3, [ head(['序号', '癌种', '核心检测基因与变异类型（最低要求）'], W3),
  ...D.proj.map(([t, d], i) => { const b = i === D.proj.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [cell(String(i + 1), W3[0], { center: true, bottom: b }),
      cell(t, W3[1], { bottom: b }), cell(d, W3[2], { bottom: b })] }); }) ]));
k.push(new Paragraph({ children: runs('注：上列为各癌种的**核心检测基因，属最低检测范围要求**，投标产品的检测范围可宽于上列内容，**覆盖更多靶点的产品不因此受限**。检测项目的收费按江苏省现行医疗服务价格政策执行，现行适用收费编码 012100000200000「高通量测序法检测费（病理样本）」，按项目分为 4,500 元、7,000 元、9,900 元等档次；具体产品适用的档次与最终开展范围，以院方完成新增项目论证与物价备案后的结果为准。', { size: 19 }),
  spacing: { before: 90, after: 120, line: 320 }, indent: { firstLine: 380 }, alignment: AlignmentType.BOTH }));

k.push(H2('报价要求'));
k.push(CAP('表 4　报价口径'));
const W4 = [1700, 8160];
const QUOTE = [
 ['设备', '按附件一整包报价，含运输、就位、安装、调试与场地适配。**设备款于最终验收合格后一次性支付；设备所有权自最终验收合格之日起归院方所有。**'],
 ['检测试剂', '以**所对应检测项目的收费标准为基准**报价，**所报试剂单价不高于该收费标准的 ＿＿ ％**，该比例在服务期内保持不变。**服务期内医疗服务价格政策调整的，按调整后的收费标准与所报比例执行。**所投试剂纳入国家或省级集中带量采购范围的，按中选结果执行。试剂款按实际供货结算，结算账期由双方在合同中约定。'],
 ['维保', '质保期满后的维保价格一并报出，作为评审因素。'],
 ['移机服务', '服务期内因院方场地调整需要移机的，**单独报出移机服务价格，作为可选报价项，不计入评标价**，中标后由院方按实际需要决定是否实施；移机不影响原质保期的连续计算。'],
];
k.push(table(W4, [ head(['报价内容', '口径'], W4),
  ...QUOTE.map(([a, b2], i) => { const b = i === QUOTE.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [cell(a, W4[0], { bottom: b }), cell(b2, W4[1], { bottom: b })] }); }) ]));

k.push(H2('附件一　设备清单'));
k.push(P('本清单按功能分区列明，共 ' + D.total + ' 项，**由中标人全部供应**。清单以设备通用名称与技术参数描述需求，**不指定品牌与型号**；投标人应逐项应答所投产品的品牌、型号与技术参数。基因测序仪的要求见表 1。'));
k.push(CAP('附表 1　配套设备与器具清单'));
const W5 = [1200, 1400, 1600, 3660, 600, 1400];
const eq = [head(['功能分区', '步骤', '设备名称', '参数要求', '数量', '用途'], W5)];
D.groups.forEach((g, gi) => {
  g.rows.forEach((r, ri) => {
    const last = gi === D.groups.length - 1 && ri === g.rows.length - 1;
    const b = last ? THICK : HAIR;
    // 功能分区与步骤两列纵向合并，对齐参照文本的表结构
    const merge = ri === 0 ? VerticalMergeType.RESTART : VerticalMergeType.CONTINUE;
    eq.push(new TableRow({ children: [
      cell(ri === 0 ? g.zone : '', W5[0], { bottom: b, merge }),
      cell(ri === 0 ? g.step : '', W5[1], { bottom: b, merge }),
      cell(r[0], W5[2], { bottom: b }), cell(r[1], W5[3], { bottom: b }),
      cell(String(r[2]), W5[4], { center: true, bottom: b }), cell(r[3], W5[5], { bottom: b }),
    ]}));
  });
});
k.push(table(W5, eq));

k.push(new Paragraph({ children: [run('苏州市立医院分子诊断中心', { hei: true, bold: true })],
  alignment: AlignmentType.RIGHT, spacing: { before: 400, line: LINE }, indent: { right: 400 } }));
k.push(new Paragraph({ children: [run('二〇二六年九月十日')],
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
  fs.writeFileSync('苏州市立医院-肿瘤NGS平台建设需求.docx', b);
  console.log('已生成 docx:', (b.length / 1024).toFixed(0), 'KB');
});
