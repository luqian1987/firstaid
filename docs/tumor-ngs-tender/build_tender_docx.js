const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
        AlignmentType, BorderStyle, ShadingType, Footer, PageNumber, VerticalAlign,
        PageOrientation } = require('docx');
// 数据每次由 build_tender.py 现导，避免 Word 版落后于 HTML 版
require('child_process').execSync('python3 export_docx_data.py', { stdio: 'inherit' });
const D = JSON.parse(fs.readFileSync('tender_docx_data.json', 'utf8'));

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

function cell(text, w, o = {}) {
  const lines = Array.isArray(text) ? text : [text];
  return new TableCell({ width: { size: w, type: WidthType.DXA },
    borders: { top: o.top || NONE, bottom: o.bottom || HAIR, left: NONE, right: NONE },
    shading: o.shade ? { type: ShadingType.CLEAR, fill: o.shade, color: 'auto' } : undefined,
    columnSpan: o.span, verticalAlign: VerticalAlign.TOP,
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

k.push(H2('一、项目概况'));
k.push(P('（一）**项目名称**：苏州市立医院分子诊断中心肿瘤 NGS 平台采购。'));
k.push(P('（二）**采购范围**：基因测序仪 1 台、配套设备与器具（详见附件一）、拟开展检测项目所需的检测试剂（详见附件二），以及相应的安装调试、培训、性能验证配合与售后服务。**本项目为整体采购，上述内容应由同一投标人整体投标，不接受分包，不接受联合体投标；所投产品应为本国产品，不接受进口产品投标。**'));
k.push(P('（三）**场地条件**：本项目实验室已建成并具备功能分区，功能分区自上游至下游依次为试剂准备区、标本与文库制备区、血浆文库制备区、杂交捕获区、文库扩增与检测区、测序区。中标人应在设备进场前完成现场勘察，就设备就位所需的台面承重、供电、给排水、温湿度与网络接入等条件提出书面要求；**因设备就位需对既有实验台面及配套设施进行局部适配调整的，由中标人负责实施，费用计入投标报价**。'));
k.push(P('（四）**供货范围**：附件一为本项目所需设备与器具的完整清单，**由中标人全部供应**。中标人应保证清单内各项齐备并配套完整，满足平台开展临床检测的全部需要；投标人不得对清单内任何一项作缺项或以「院方自备」等方式排除。'));
k.push(P('（五）**服务期限**：自合同签订之日起 ＿＿ 年。'));

k.push(H2('二、基因测序仪技术要求'));
k.push(P('本部分以资质与功能性指标描述需求，**不指定品牌、型号、专利或供应商**。投标人可提供满足下列要求的任何产品，数量 1 台。'));
k.push(CAP('表 1　基因测序仪技术要求'));
const W1 = [700, 1900, 7260];
k.push(table(W1, [ head(['序号', '项目', '要求'], W1),
  ...D.tech.map(([t, d], i) => { const b = i === D.tech.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [cell(String(i + 1), W1[0], { center: true, bottom: b }),
      cell(t, W1[1], { bottom: b }), cell(d, W1[2], { bottom: b })] }); }) ]));

k.push(H2('三、配套设备与器具'));
k.push(P('（一）配套设备与器具的名称、技术参数与数量详见附件一，按功能分区列明。'));
k.push(P('（二）附件一以设备通用名称与技术参数描述需求，**不指定品牌与型号**。投标人应逐项应答所投产品的品牌、型号与技术参数，并提供满足参数要求的证明材料。'));
k.push(P('（三）附件一所列为设备与器具，不含检测试剂与实验耗材。'));

k.push(H2('四、检测试剂'));
k.push(P('（一）**范围**：本次采购包含附件二所列拟开展检测项目对应的检测试剂。每一癌种可包含多个检测项目及多个试剂盒，具体清单由投标人在投标文件中逐项列明。'));
k.push(P('（二）**注册合规**：所投试剂盒须已取得国家药品监督管理局第三类医疗器械注册证，注册证在有效期内，注册证载明的适用范围覆盖所对应的癌种，**且载明的适用机型包含所投基因测序仪机型**。投标人须逐项提供试剂盒名称、注册证编号、注册适用范围与适用机型。'));
k.push(P('（三）**报价方式**：试剂以**折扣率**形式报价，基准价为生产厂家公开挂牌价或省级药品（医用耗材）集中采购平台挂网价，投标人须提供基准价的依据材料。**试剂报价原则上不高于基准价的五折**。所报折扣率在服务期内保持不变；基准价发生调整的，按调整后的基准价与所报折扣率执行。'));
k.push(P('（四）**性能验证**：所投试剂盒须通过院方组织的方法学性能验证方可用于临床检测，验证结论由院方确认；未通过验证的产品应予更换。'));
k.push(P('（五）**供应保障**：中标人应保证试剂在服务期内的持续稳定供应，并按院方需求提供冷链配送。'));

k.push(H2('五、服务要求'));
k.push(P('（一）**供应、安装与调试**。负责所供设备的运输、就位、安装与调试，直至各功能分区具备开展临床检测的条件。'));
k.push(P('（二）**培训与技术转移**。对院方指定人员进行系统培训，内容覆盖样本前处理、文库构建、杂交捕获、上机测序、数据分析与报告解读全流程，**直至院方人员具备独立操作能力**；并提供检测项目的临床沟通与疑难病例报告解读支持。'));
k.push(P('（三）**人员配置**。中标人应指定项目负责人一名，并**按项目实际需要配备具备分子诊断或临床检验相关背景的技术人员不少于 1 名，参与日常项目的技术对接、培训带教与运行配合**；其工作范围为技术支持与运行配合，检验报告由院方具备相应资质的人员审核签发。中标人人员进入实验室应遵守院方生物安全、感染控制与信息安全的相关规定，并签署保密承诺。'));
k.push(P('（四）**质量与售后**。配合院方建立本平台检测项目的标准操作规程及相关质量管理体系文件，配合完成方法学性能验证与室间质评；提供设备的日常维护、故障响应与备件供应。'));

k.push(H2('六、商务要求'));
k.push(P('（一）**交付与验收**。设备到货、安装调试完成后由院方组织验收，验收内容包括设备功能与技术参数复核，以及拟开展项目的方法学性能验证。交付与安装期限由双方在合同中约定。'));
k.push(P('（二）**付款**。**设备款于最终验收合格后一次性支付；试剂款按实际供货结算**，结算账期由双方在合同中约定。'));
k.push(P('（三）**质保与维保**。中标人应提供设备质保，质保期限、故障响应与到场时限由双方在合同中约定；质保期满后的维保价格，投标人应在投标文件中一并报出。'));
k.push(P('（四）**设备所有权**。**本次采购设备的所有权自最终验收合格之日起归院方所有。**'));
k.push(P('（五）**移机服务**。服务期内因院方场地调整需要移机的，投标人须**单独报出移机服务价格**，作为可选报价项单独列示，不计入评标价，中标后由院方按实际需要决定是否实施；移机不影响原质保期的连续计算。'));
k.push(P('（六）**数据安全**。本平台产生的检测数据归院方所有。分析解读软硬件应支持院内本地化部署，**检测数据应存储于院内，不得上传至院外，不得出境**；涉及人类遗传资源的活动，应符合《中华人民共和国人类遗传资源管理条例》及其实施细则的规定。'));

k.push(H2('七、投标人资格与合规要求'));
k.push(P('（一）**资格要求**。投标人应具备下列条件：'));
['1. 具有独立法人资格，具备有效的营业执照；',
 '2. 具备《医疗器械经营许可证》或第二类医疗器械经营备案凭证，经营范围覆盖所投产品类别；',
 '3. 取得所投产品制造商针对本项目的授权文件；',
 '4. 具有同类临床基因测序平台的供货与服务业绩，并能提供相应合同或验收证明；',
 '5. 具备境内的技术服务与备件供应体系，能够保障服务期内设备维保与试剂供应的连续性。'
].forEach(t => k.push(P(t, { left: 420 })));
k.push(P('（二）**廉洁承诺**。投标人应出具书面承诺：不以捐赠资助、科研合作、学术会议、外出考察等任何名义，向院方工作人员输送利益或提供与本项目采购相挂钩的资源。'));
k.push(P('（三）**其他**。本文件为采购需求，未尽事宜以招标文件其他章节及采购合同约定为准。'));

k.push(H2('附件一　配套设备与器具清单'));
k.push(P('本清单按功能分区列明，共 ' + D.total + ' 项，**由中标人全部供应**。清单以设备通用名称与技术参数描述需求，不指定品牌与型号。基因测序仪的要求见正文第二部分。'));
k.push(CAP('附表 1　配套设备与器具清单'));
const W3 = [2400, 6660, 800];
const eq = [head(['设备名称', '技术参数要求', '数量'], W3)];
D.rooms.forEach((R, gi) => {
  eq.push(new TableRow({ children: [cell(R.zone, CW, { span: 3, hei: true, bold: true, shade: 'F0F0F0', bottom: HAIR })] }));
  R.rows.forEach((r, ri) => {
    const last = gi === D.rooms.length - 1 && ri === R.rows.length - 1;
    const b = last ? THICK : HAIR;
    eq.push(new TableRow({ children: [cell(r[0], W3[0], { bottom: b }), cell(r[1], W3[1], { bottom: b }),
      cell(String(r[2]), W3[2], { center: true, bottom: b })] }));
  });
});
k.push(table(W3, eq));

k.push(H2('附件二　拟开展检测项目'));
k.push(P('本平台首批拟开展下列癌种的检测项目。每一癌种可包含多个检测项目及多个试剂盒，具体清单由投标人在投标文件中逐项列明，并须符合正文第四部分的注册合规与性能验证要求。'));
k.push(CAP('附表 2　首批拟开展检测项目'));
const W4 = [700, 2000, 7160];
k.push(table(W4, [ head(['序号', '癌种', '核心检测基因与变异类型（最低要求）'], W4),
  ...D.proj.map(([t, d], i) => { const b = i === D.proj.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [cell(String(i + 1), W4[0], { center: true, bottom: b }),
      cell(t, W4[1], { bottom: b }), cell(d, W4[2], { bottom: b })] }); }) ]));
k.push(new Paragraph({ children: runs('注：上列为各癌种的**核心检测基因，属最低检测范围要求**。投标产品的检测范围可宽于上列内容，**覆盖更多靶点的产品不因此受限**；投标人应在投标文件中列明所投产品的完整检测范围。上述检测项目适用收费编码 012100000200000「高通量测序法检测费（病理样本）」。检测项目的最终开展范围，以院方完成新增项目论证与物价备案后的结果为准。', { size: 19 }),
  spacing: { before: 90, after: 120, line: 320 }, indent: { firstLine: 380 }, alignment: AlignmentType.BOTH }));

k.push(new Paragraph({ children: [run('苏州市立医院分子诊断中心', { hei: true, bold: true })],
  alignment: AlignmentType.RIGHT, spacing: { before: 400, line: LINE }, indent: { right: 400 } }));
k.push(new Paragraph({ children: [run('二〇二六年九月九日')],
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
  fs.writeFileSync('苏州市立医院-肿瘤NGS平台招标需求.docx', b);
  console.log('已生成 docx:', (b.length / 1024).toFixed(0), 'KB');
});
