const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
        AlignmentType, BorderStyle, ShadingType, Footer, PageNumber, VerticalAlign,
        PageOrientation } = require('docx');
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
k.push(new Paragraph({ children: [run('建设地点：太湖新城总院区病理科现有 PCR 多分区实验室', { size: 21, color: '444444' })],
  alignment: AlignmentType.CENTER, spacing: { after: 220 },
  border: { bottom: { style: BorderStyle.DOUBLE, size: 6, color: '000000', space: 10 } } }));

// 提示框用单格表格实现：docx-js 生成 pBdr 时的子元素顺序不符合 OOXML 要求，
// 同时带上下框线的段落无法通过 schema 校验，改用表格边框
const BOX = { style: BorderStyle.SINGLE, size: 6, color: '000000' };
k.push(new Table({ columnWidths: [CW], width: { size: CW, type: WidthType.DXA },
  borders: { top: BOX, left: BOX, bottom: BOX, right: BOX, insideHorizontal: NONE, insideVertical: NONE },
  rows: [new TableRow({ children: [new TableCell({
    width: { size: CW, type: WidthType.DXA },
    margins: { top: 120, bottom: 120, left: 160, right: 160 },
    children: [
      new Paragraph({ children: [run('拟稿说明（发文前请整体删除本框及全文各处「拟稿说明」段落）', { hei: true, bold: true, size: 19 })],
        spacing: { after: 60, line: 320 } }),
      new Paragraph({ children: runs('本文件为招标需求征求意见稿。文中以下划线标示的数值、期限与比例，需由院方按实际标本量、预算与内控要求填定；各处「拟稿说明」为起草依据与风险提示，供院内讨论使用，不属于招标文件正文。', { kai: true, size: 19 }),
        spacing: { line: 320 }, alignment: AlignmentType.BOTH }),
    ] })] })] }));
k.push(new Paragraph({ text: '', spacing: { after: 200 } }));

/* 一 */
k.push(H2('一、项目概况'));
k.push(P('（一）**项目名称**：苏州市立医院分子诊断中心肿瘤 NGS 平台设备采购。'));
k.push(P('（二）**建设地点**：太湖新城总院区病理科现有 PCR 多分区实验室。'));
k.push(P('（三）**建设方式**：依托现有六间 PCR 功能分区实验室及其配套缓冲间，**不涉及新建与装修改造，仅作功能分配与设备进场**。六间功能分区自上游至下游依次为：试剂准备区（试剂准备间）、标本与文库制备区（PCR2）、血浆文库制备区（PCR3）、杂交捕获区（PCR4）、文库扩增与检测区（PCR5）、测序区（PCR8）。'));
k.push(P('（四）**采购范围**：测序平台及配套设备的供应、运输、安装、调试、培训与售后服务。**检测试剂与耗材不在本次采购范围内，另行组织采购**，相关要求见第七部分第（六）项。'));
k.push(P('（五）**服务期限**：自合同签订之日起 ＿＿ 年。'));
k.push(DN('拟稿说明｜关于建设方式。原参照文本中列有「负责实验室场地设计、装修」一项。本项目场地为病理科现有已建成的 PCR 多分区实验室，无新建与装修改造需求，故不设该项，相应费用亦不计入本次采购。'));

/* 二 */
k.push(H2('二、测序平台技术要求'));
k.push(P('本部分以技术参数与性能指标描述采购需求，**不指定品牌、型号、专利或供应商**。投标人可提供满足或优于下列指标的任何产品。'));
k.push(CAP('表 1　测序平台技术要求'));
const W1 = [700, 1900, 7260];
k.push(table(W1, [ head(['序号', '项目', '技术要求'], W1),
  ...D.tech.map(([t, d], i) => { const b = i === D.tech.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [cell(String(i + 1), W1[0], { center: true, bottom: b }),
      cell(t, W1[1], { bottom: b }), cell(d, W1[2], { bottom: b })] }); }) ]));
k.push(DN('拟稿说明｜关于参数设置。表中留空的通量、读长、运行时长等数值，应由院方按预计年标本量与拟开展 panel 的规模确定。参数区间需保证不少于三家潜在投标人能够满足；将参数收窄至仅一款机型可达，属于以技术要求指向特定产品，与《招标投标法实施条例》第三十二条、《政府采购法实施条例》第二十条的规定不符，且易被质疑。'));

/* 三 */
k.push(H2('三、设备配置要求'));
k.push(P('（一）**配置原则**。附件一按六个功能分区列明设备与器具的通用名称、技术参数与数量，共 91 项。**实验室现有设备经核验符合参数要求的予以沿用，缺配部分由中标人按附件一补齐**。'));
k.push(P('（二）**关于参考型号**。附件一「参考型号」列仅用于说明参数对应的产品形态，**投标人可提供同等或优于该参数的其他品牌型号，不得以未采用参考型号为由作否定性评价**。'));
k.push(P('（三）**关于耗材**。附件一为设备与器具，不含试剂与耗材。'));
k.push(DN('拟稿说明｜关于品牌型号。原参照文本正文以「品牌 + 型号 + 不得更换」的方式列示三台测序仪，附件清单亦逐项指定厂商。此种写法属于限定或指定特定品牌、供应商，构成对潜在投标人的不合理限制。本稿已改为「通用名称 + 技术参数 + 参考型号（或同等）」，并在正文明确不得因未采用参考型号作否定性评价。'));

/* 四 */
k.push(H2('四、服务内容'));
[['（一）**设备供应、运输、安装与调试**。中标人负责附件一所列设备的供应、运输、就位、安装与调试，直至各功能分区具备开展临床检测的条件，并负责与院方现有设备的衔接核验。'],
 ['（二）**质量管理体系文件与性能验证支持**。协助建立本平台检测项目的标准操作规程及相关质量管理体系文件；协助完成方法学性能验证（精密度、正确度、检出限、可报告范围等）；协助院方参加室间质评并上报结果。'],
 ['（三）**技术培训与技术转移**。对院方指定人员进行系统培训，内容覆盖样本前处理、文库构建、杂交捕获、上机测序、数据分析与报告解读全流程，**直至院方人员具备独立操作与独立出具报告的能力**。培训应形成书面记录与考核结论。'],
 ['（四）**临床沟通与报告解读支持**。提供检测项目的临床沟通、疑难病例报告解读的技术支持；配合院方开展面向临床科室的技术交流。'],
 ['（五）**售后服务与维保**。提供设备的日常维护、故障响应与备件供应，具体要求见第七部分第（四）项。'],
 ['（六）**应急保障**。按第六部分要求提供应急响应。']].forEach(([t]) => k.push(P(t)));
k.push(DN('拟稿说明｜关于删除的两项。原参照文本列有「负责项目推广（专人负责市场运营和品牌支持、区域业务拓展）」与「科研支持（提供驻场博士，协助文章发表与标书撰写）」两项，本稿均未纳入。前者属供应商自身商业行为，不构成医院采购标的；后者不属于本次采购标的，将科研人力、论文与课题协助作为供应商义务写入采购文件，实质是以采购权换取科研资源，企业人员代写论文、代写基金申报材料亦与科研诚信管理要求相悖。医企科研合作应另案另签，经医院科研管理部门立项与伦理审查，经费入院统一管理，与设备试剂采购完全脱钩。'));

/* 五 */
k.push(H2('五、人员与培训要求'));
k.push(P('（一）中标人应指定项目负责人一名，并配备具备分子诊断与 NGS 技术背景的技术支持人员，负责安装调试、培训带教与技术响应。'));
k.push(P('（二）驻场技术支持人员的工作范围限于设备调试、技术培训、方法学验证配合与故障处理。**临床检验的实际操作与检验报告的出具，由院方具备相应资质的人员承担**；中标人人员不得从事出具临床报告的检测操作。'));
k.push(P('（三）中标人人员进入实验室，应遵守院方生物安全、感染控制、信息安全与廉洁从业的相关规定，并签署保密承诺。'));
k.push(P('（四）培训完成并经院方考核合格后，驻场支持转为定期回访与按需响应。'));
k.push(DN('拟稿说明｜关于人员派遣。原参照文本要求供应商「派遣 2 名具有 PCR 上岗证书的湿实验操作人员」。《医疗机构临床实验室管理办法》要求临床检验工作由本机构具备资质的人员实施；非本院人员直接从事出具临床报告的检测操作，涉及执业资质与医疗责任归属问题。本稿已将供应商人员的职责限定为培训与技术支持。'));

/* 六 */
k.push(H2('六、应急保障'));
k.push(P('中标人应就下列情形制定应急预案并在合同中约定响应时限，保障检测报告的时效性与准确性。'));
k.push(CAP('表 2　应急情形与响应要求'));
const W2 = [2200, 7660];
k.push(table(W2, [ head(['应急情形', '响应要求'], W2),
  ...D.emerg.map(([a, b2], i) => { const b = i === D.emerg.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [cell(a, W2[0], { bottom: b }), cell(b2, W2[1], { bottom: b })] }); }) ]));
k.push(DN('拟稿说明｜关于标本外送。原参照文本在应急方案中直接写明外送至某一具体公司的实验室。在招标需求中指名特定供应商的设施，构成对标的归属的指向。本稿改为以资质与能力描述受托机构，不出现公司名称。外送涉及患者知情同意、样本与数据出院流向，应另行签订委托检验协议并报院方医务管理部门备案。'));

/* 七 */
k.push(H2('七、商务要求'));
k.push(P('（一）**交货与安装期限**。合同签订后 ＿＿ 日历天内完成全部设备到货、安装与调试，并具备验收条件。'));
k.push(P('（二）**验收标准**。验收分三个环节：设备到货验收（数量、型号、外观、随机文件）；安装调试验收（各设备功能与技术参数复核）；平台运行验收（完成方法学性能验证，并支持院方通过临床基因扩增检验实验室技术审核）。三个环节全部合格后签署最终验收报告。'));
k.push(P('（三）**付款节点**。合同生效后支付 ＿＿ ％；全部设备到货并安装调试合格后支付 ＿＿ ％；最终验收合格后支付 ＿＿ ％；余款 ＿＿ ％ 作为质量保证金，质保期满无质量问题后支付。'));
k.push(P('（四）**质保与维保**。自最终验收合格之日起提供 ＿＿ 年免费质保。质保期内故障响应不超过 ＿＿ 小时，到场时间不超过 ＿＿ 小时，核心设备无法在 ＿＿ 小时内修复的应提供备机。质保期满后的维保价格，投标人应在投标文件中一并报出并作为评审因素。'));
k.push(P('（五）**设备所有权**。**本次采购设备的所有权自最终验收合格之日起归院方所有**，中标人不得设置任何形式的使用限制或与后续试剂采购相挂钩的条件。'));
k.push(P('（六）**检测试剂与耗材**。检测试剂与耗材不在本次采购范围内，将另行组织采购。投标人须在投标文件中就下列事项作出书面说明，并作为评审因素：'));
k.push(P('1. **平台开放性**：所投测序平台为封闭系统或开放系统，可使用的检测试剂来源范围；若为封闭系统，应明确说明。', { left: 420 }));
k.push(P('2. **配套试剂的注册状态**：拟配套使用的检测试剂盒的注册证编号及其载明的适用机型。', { left: 420 }));
k.push(P('3. **试剂价格承诺**：服务期内配套试剂的单价承诺或价格上限，及价格调整机制。', { left: 420 }));
k.push(P('上述三项与设备报价一并纳入**全生命周期成本评审**。'));
k.push(P('（七）**数据权属与信息安全**。本平台产生的全部检测数据、原始下机数据及衍生数据，**所有权归院方所有**。中标人及其人员因技术支持接触院方数据的，限于履行本合同之目的，不得留存、复制、对外提供或用于自身研发；涉及人类遗传资源的，应遵守《人类遗传资源管理条例》及其实施细则的规定。合同终止或人员撤场时，应完成数据交接与本地留存的清除，并出具书面确认。'));
k.push(P('（八）**违约与退出**。合同应约定交付逾期、验收不合格、响应超时的违约责任；服务期满或提前终止时，中标人应完成设备资料、系统账号、方法文件与在院数据的完整交接，不得以任何方式影响检测工作的连续性。'));
k.push(DN('拟稿说明｜关于设备与试剂的关系。「设备低价供应、后端以试剂回收」是监管重点关注的结构。本稿采取的处理方式是：设备买断、所有权归院方（第五项），试剂明确排除在本次采购之外并另行组织采购（第六项），同时要求投标人披露平台开放性并提供试剂价格承诺，纳入全生命周期成本评审。如此既避免了设备与试剂的捆绑，也使院方在设备采购阶段即可掌握后续试剂的成本口径。另需提示：《招标投标法》第三十三条规定投标人不得以低于成本的报价竞标，设备报价明显低于市场水平的，投标人应在投标文件中说明其合理性依据。'));

/* 八 */
k.push(H2('八、投标人资格与合规要求'));
k.push(P('（一）**资格要求**。投标人应具备下列条件：'));
['1. 具有独立法人资格，具备有效的营业执照；',
 '2. 具备《医疗器械经营许可证》或第二类医疗器械经营备案凭证，经营范围覆盖所投产品类别；',
 '3. 取得所投产品制造商针对本项目的授权文件；',
 '4. 近 ＿＿ 年内具有同类临床基因测序平台的供货与服务业绩，并能提供合同或验收证明；',
 '5. 具备本地化服务能力，能够满足本文件约定的故障响应与到场时限；',
 '6. 未被列入失信被执行人、政府采购严重违法失信行为记录名单及医药购销领域商业贿赂不良记录。'
].forEach(t => k.push(P(t, { left: 420 })));
k.push(P('（二）**廉洁与合规承诺**。投标人应出具书面承诺：不以捐赠资助、科研合作、学术会议、外出考察等任何名义，向院方工作人员输送利益或提供与采购相挂钩的资源；不通过第三方实施上述行为。经查实的，院方有权解除合同并追究责任。'));

/* 附件一 */
k.push(H2('附件一　设备配置清单'));
k.push(P('本清单按六个功能分区列明，共 91 项。「参考型号」列仅用于说明参数对应的产品形态，**投标人可提供同等或优于该参数的其他品牌型号**。'));
k.push(CAP('附表 1　设备与器具配置清单（按功能分区，共 91 项）'));
const W3 = [1900, 4200, 2960, 800];
const eq = [head(['设备名称', '技术参数要求', '参考型号（或同等）', '数量'], W3)];
D.rooms.forEach((R, gi) => {
  eq.push(new TableRow({ children: [cell(`${R.key}　${R.zone}　（${R.kinds} 项）`, CW,
    { span: 4, hei: true, bold: true, shade: 'F0F0F0', bottom: HAIR })] }));
  R.rows.forEach((r, ri) => {
    const last = gi === D.rooms.length - 1 && ri === R.rows.length - 1;
    const b = last ? THICK : HAIR;
    eq.push(new TableRow({ children: [cell(r[0], W3[0], { bottom: b }), cell(r[1], W3[1], { bottom: b }),
      cell(r[2], W3[2], { bottom: b }), cell(String(r[3]), W3[3], { center: true, bottom: b })] }));
  });
});
k.push(table(W3, eq));

/* 附件二 */
k.push(H2('附件二　拟开展检测项目'));
k.push(P('下列检测项目所用试剂盒均已取得国家药品监督管理局第三类医疗器械注册证，共用收费编码 012100000200000「高通量测序法检测费（病理样本）」，价格已在物价目录内。**本附件用于说明平台的预期检测用途，不构成本次采购标的**。'));
k.push(CAP('附表 2　拟开展检测项目（试剂另行采购）'));
const W4 = [700, 4200, 2100, 1560, 1300];
k.push(table(W4, [ head(['序号', '试剂盒名称', '注册证编号', '注册适用范围', '物价收费'], W4),
  ...D.kits.map((x, i) => { const b = i === D.kits.length - 1 ? THICK : HAIR;
    return new TableRow({ children: [cell(x.no, W4[0], { center: true, bottom: b }),
      cell(x.name, W4[1], { bottom: b }), cell(x.reg, W4[2], { bottom: b }),
      cell(x.scope, W4[3], { bottom: b }), cell(x.price + ' 元', W4[4], { right: true, bottom: b })] }); }) ]));

k.push(new Paragraph({ children: runs('以上招标需求，请各位领导及相关职能部门审阅并提出修改意见。'),
  spacing: { before: 280, after: 160, line: LINE }, indent: { firstLine: IND }, alignment: AlignmentType.BOTH }));
k.push(new Paragraph({ children: [run('苏州市立医院分子诊断中心', { hei: true, bold: true })],
  alignment: AlignmentType.RIGHT, spacing: { before: 320, line: LINE }, indent: { right: 400 } }));
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
  fs.writeFileSync('苏州市立医院-肿瘤NGS平台招标需求（征求意见稿）.docx', b);
  console.log('已生成 docx:', (b.length / 1024).toFixed(0), 'KB');
});
