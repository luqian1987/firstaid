"""位置示意图。

**画的是示意图，不是他的影像。** 我们手里没有原始影像，
所以图上只做一件事：告诉他这个发现在身体的哪个位置。
不表现程度、不表现大小、不画病变本身——那些都是编造。

每张图导出一个函数，接受 mark（高亮哪个部位），返回内联 SVG。
mark 认不出来时不高亮，而不是随便标一个地方。
"""
from __future__ import annotations

import html as H

C = {"ink": "#1B2127", "mute": "#8D959E", "line": "#C9D0D6",
     "act": "#A8452A", "actbg": "#F7EDE9", "calm": "#1F5E56",
     "vessel": "#B8C2CB", "organ": "#DCE3E8", "paper": "#FCFDFD"}


def _lbl(x, y, t, size=10.5, fill=None, weight=500, anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill or C["mute"]}" text-anchor="{anchor}" '
            f'font-family="PingFang SC,Hiragino Sans GB,Microsoft YaHei,sans-serif">'
            f'{H.escape(str(t), quote=False)}</text>')


def _pin(x, y, label):
    """高亮点：呼吸环 + 标注。整张图上只有这一个强调。"""
    return (f'<g><circle cx="{x}" cy="{y}" r="7" fill="none" stroke="{C["act"]}" '
            f'stroke-width="2"><animate attributeName="r" values="7;19" dur="2.6s" '
            f'repeatCount="indefinite"/><animate attributeName="opacity" '
            f'values=".85;0" dur="2.6s" repeatCount="indefinite"/></circle>'
            f'<circle cx="{x}" cy="{y}" r="5.5" fill="{C["act"]}"/></g>'
            + _lbl(x, y - 16, label, 11.5, C["act"], 700))


def cerebral_arteries(mark: str | None = None) -> str:
    """颅底动脉环（Willis 环）示意，俯视。

    画到"认得出这是血管环"为止：前循环（颈内动脉 → 大脑前/中动脉）
    与后循环（椎—基底动脉 → 大脑后动脉）由前后交通支连成一圈。
    粗细只区分主干与交通支，不表示任何人的实际管径。
    """
    P = {"mca_m1_left": (206, 150, "左侧大脑中动脉 M1 段"),
         "mca_m1_right": (94, 150, "右侧大脑中动脉 M1 段"),
         "basilar": (150, 214, "基底动脉"),
         "ica_left": (178, 150, "左侧颈内动脉"),
         "ica_right": (122, 150, "右侧颈内动脉")}
    W, Hh = 300, 286
    s = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" '
         f'aria-label="颅底动脉环示意图" style="max-width:300px;display:block">',
         f'<rect width="{W}" height="{Hh}" fill="{C["paper"]}"/>',
         _lbl(150, 18, "颅底动脉环（示意，非本人影像）", 10, C["mute"], 600)]
    main = (f'stroke="{C["vessel"]}" stroke-width="7" fill="none" '
            f'stroke-linecap="round"')
    comm = (f'stroke="{C["vessel"]}" stroke-width="4" fill="none" '
            f'stroke-linecap="round"')
    s += [
        # 大脑前动脉：由前交通支相连的两支，向前上走
        f'<path d="M136 96 C132 74 130 62 133 52" {main}/>',
        f'<path d="M164 96 C168 74 170 62 167 52" {main}/>',
        f'<path d="M136 98 L164 98" {comm}/>',                     # 前交通动脉
        # 颈内动脉末端：从下方上行，在环的前外侧分出大脑前与大脑中
        f'<path d="M122 168 C120 140 126 112 136 96" {main}/>',
        f'<path d="M178 168 C180 140 174 112 164 96" {main}/>',
        # 大脑中动脉 M1 段：由颈内动脉末端向外侧横行
        f'<path d="M124 152 C150 140 182 140 206 150 L236 158" {main}/>',
        f'<path d="M176 152 C150 140 118 140 94 150 L64 158" '
        f'stroke="{C["vessel"]}" stroke-width="7" fill="none" '
        f'stroke-linecap="round" opacity="0"/>',
        f'<path d="M122 152 L64 160" {main}/>',                    # 右 M1
        f'<path d="M178 152 L236 160" {main}/>',                   # 左 M1
        # 后交通动脉：把颈内动脉与大脑后动脉连起来，这是"环"合拢的地方
        f'<path d="M122 168 C118 186 116 198 118 208" {comm}/>',
        f'<path d="M178 168 C182 186 184 198 182 208" {comm}/>',
        # 大脑后动脉，由基底动脉顶端分出
        f'<path d="M118 208 L66 220" {main}/>',
        f'<path d="M182 208 L234 220" {main}/>',
        f'<path d="M118 208 C132 202 168 202 182 208" {main}/>',
        # 椎—基底动脉
        f'<path d="M150 272 C148 250 148 230 150 212" {main}/>',
        f'<path d="M150 272 L132 284" {main}/>',
        f'<path d="M150 272 L168 284" {main}/>',
        _lbl(150, 40, "前（额部）", 9.5),
        _lbl(114, 196, "后交通", 9, anchor="end"),
        _lbl(150, 238, "基底动脉", 9.5),
        _lbl(190, 280, "椎动脉", 9.5, anchor="start"),
        _lbl(60, 176, "大脑中动脉", 9.5),
        _lbl(240, 176, "大脑中动脉", 9.5),
        _lbl(150, 112, "前交通", 9, anchor="middle"),
    ]
    if mark in P:
        x, y, label = P[mark]
        s.append(_pin(x, y, label))
    s.append("</svg>")
    return "".join(s)


def carotid(mark: str | None = None) -> str:
    """颈动脉分叉示意，正面观。

    斑块最常见的落点就是分叉处那段略膨大的球部——画它是为了说明
    "为什么偏偏长在这儿"：血流在分叉处分层、剪切力低，内膜最先受累。
    正面观下图的左侧是本人的右侧，这一句必须写出来，否则一定有人看反。
    """
    P = {"bulb_right": (108, 132, "右侧颈动脉球部"),
         "bulb_left": (192, 132, "左侧颈动脉球部"),
         "cca": (150, 216, "颈总动脉")}
    W, Hh = 300, 258
    s = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" '
         f'aria-label="颈动脉分叉示意图" style="max-width:300px;display:block">',
         f'<rect width="{W}" height="{Hh}" fill="{C["paper"]}"/>',
         _lbl(150, 18, "颈动脉分叉（示意，非本人影像）", 10, C["mute"], 600)]
    v = (f'stroke="{C["vessel"]}" stroke-width="7" fill="none" '
         f'stroke-linecap="round"')
    for side in (-1, 1):
        cx = 150 + side * 42          # 球部中心
        s += [
            # 颈内动脉：从球部往上，略偏外
            f'<path d="M{cx} 132 C{cx + side*2} 100 {cx + side*6} 72 '
            f'{cx + side*8} 46" {v}/>',
            # 颈外动脉：从球部往上，偏内侧且略细
            f'<path d="M{cx} 132 C{cx - side*8} 104 {cx - side*14} 78 '
            f'{cx - side*18} 52" stroke="{C["vessel"]}" stroke-width="5.5" '
            f'fill="none" stroke-linecap="round"/>',
            # 球部：分叉处那段膨大
            f'<ellipse cx="{cx}" cy="{132}" rx="9" ry="13" '
            f'fill="{C["vessel"]}"/>',
            # 颈总动脉：从球部往下，向中线收拢
            f'<path d="M{cx} 140 C{cx - side*2} 170 {cx - side*6} 196 '
            f'{cx - side*10} 224" {v}/>',
            _lbl(cx + side*24, 44, "颈内", 9.5),
            _lbl(cx - side*30, 50, "颈外", 9.5),
            _lbl(cx - side*4, 240, "颈总", 9.5),
        ]
    s.append(_lbl(150, 254, "↓ 通向心脏　　图上左侧 = 你的右侧", 9, C["mute"], 600))
    if mark in P:
        x, y, label = P[mark]
        s.append(_pin(x, y, label))
    s.append("</svg>")
    return "".join(s)


def thyroid(mark: str | None = None) -> str:
    """甲状腺示意。"""
    P = {"whole": (150, 120, "甲状腺（弥漫性）"),
         "right_lobe": (110, 118, "右叶"), "left_lobe": (190, 118, "左叶")}
    s = [f'<svg viewBox="0 0 300 200" width="100%" role="img" '
         f'aria-label="甲状腺示意图" style="max-width:300px;display:block">',
         f'<rect width="300" height="200" fill="{C["paper"]}"/>',
         _lbl(150, 24, "甲状腺（示意，非本人影像）", 10, C["mute"], 600),
         f'<path d="M150 74 L150 158" stroke="{C["line"]}" stroke-width="16" '
         f'fill="none" opacity=".5"/>',
         f'<path d="M132 92 C104 92 92 112 96 134 C100 154 122 158 134 144 '
         f'C142 134 142 104 132 92 Z" fill="{C["organ"]}" stroke="{C["line"]}"/>',
         f'<path d="M168 92 C196 92 208 112 204 134 C200 154 178 158 166 144 '
         f'C158 134 158 104 168 92 Z" fill="{C["organ"]}" stroke="{C["line"]}"/>',
         f'<rect x="141" y="116" width="18" height="20" rx="3" '
         f'fill="{C["organ"]}" stroke="{C["line"]}"/>',
         _lbl(150, 176, "气管在中间，两叶分列左右", 9.5)]
    if mark in P:
        x, y, label = P[mark]
        s.append(_pin(x, y, label))
    s.append("</svg>")
    return "".join(s)


DIAGRAMS = {"cerebral_arteries": cerebral_arteries,
            "carotid": carotid,
            "thyroid": thyroid}


def render_anatomy(name: str, mark: str | None = None) -> str:
    fn = DIAGRAMS.get(name)
    return fn(mark) if fn else ""
