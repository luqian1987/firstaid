"""疾病演变拓扑图的 SVG 渲染。

横轴是进展方向，不是时间轴。图上不出现任何时间表述——
"多久到下一关"需要队列数据来校准，我们没有。

三种节点状态与全系统的三态语义一致：已见 / 未见 / 判不了。
"判不了"画成虚线空心，绝不当作"没有"。
"""
from __future__ import annotations

import html as H

from ..model import StageState, Topology

C = dict(act="#A8452A", actbg="#F7EDE9", settle="#1F5E56", settlebg="#E7F0EE",
         muted="#6B757D", rule="#D2D8DC", ink="#1B2127", ink2="#3A444C", faint="#F4F6F7")
FONT = ("'PingFang SC','Hiragino Sans GB','Source Han Sans SC',"
        "'Microsoft YaHei',sans-serif")
COL_X = [352, 640, 862]
ZONES = [((200, 520), "现在所在", "本次有直接证据"),
         ((520, 770), "下一关", "本次有指标能判定"),
         ((770, 960), "再往后", "本次没有数据，不展开")]
ROW_H, TOP = 112, 100


def _t(x, y, s, size=12, fill=None, weight=400, anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill or C["ink"]}" '
            f'text-anchor="{anchor}">{H.escape(str(s), quote=False)}</text>')


def _wrap(s: str, budget: float) -> list[str]:
    """按视觉宽度折行。中日韩字符按 1 个单位算，ASCII 按 0.55。

    SVG 里的 <text> 不会自动换行，超出的部分会直接画到画布外面去
    ——上游那个"抗过氧化物酶抗体 939.6 · ……"就是这样被截掉左半边的。
    """
    lines, cur, w = [], "", 0.0
    for ch in str(s):
        cw = 0.55 if ord(ch) < 0x2E80 else 1.0
        if w + cw > budget and cur:
            lines.append(cur)
            cur, w = "", 0.0
        cur += ch
        w += cw
    if cur:
        lines.append(cur)
    return lines or [""]


def _tw(x, y, s, size=12, fill=None, weight=400, budget=18, lh=None):
    """折行版 _t。返回多行 <text>，行距默认为字号的 1.25 倍。"""
    lh = lh or size * 1.25
    return "".join(_t(x, y + i * lh, ln, size, fill, weight)
                   for i, ln in enumerate(_wrap(s, budget)))


def _node(x, y, st):
    col = {StageState.CROSSED: C["act"], StageState.CLEAR: C["settle"],
           StageState.UNKNOWN: C["muted"]}[st.state]
    bg = {StageState.CROSSED: C["actbg"], StageState.CLEAR: C["settlebg"],
          StageState.UNKNOWN: C["faint"]}[st.state]
    o = [f'<g transform="translate({x},{y})">']
    if st.emphasis:
        # 已确认的器质性发现：脉动边框
        o += [f'<rect x="-80" y="-17" width="160" height="34" rx="5" fill="none" '
              f'stroke="{C["act"]}" stroke-width="1.5">'
              f'<animate attributeName="stroke-width" values="1.5;4.5;1.5" dur="2.2s" '
              f'repeatCount="indefinite"/>'
              f'<animate attributeName="opacity" values="1;.15;1" dur="2.2s" '
              f'repeatCount="indefinite"/></rect>',
              f'<rect x="-80" y="-17" width="160" height="34" rx="5" fill="{C["actbg"]}" '
              f'stroke="{C["act"]}" stroke-width="1.5"/>',
              _t(0, 5, st.name, 12.5, C["act"], 600)]
    else:
        if st.state is StageState.CROSSED:
            # 呼吸环 = 你在这里
            o.append(f'<circle r="7" fill="none" stroke="{col}" stroke-width="2">'
                     f'<animate attributeName="r" values="7;21" dur="2.6s" '
                     f'repeatCount="indefinite"/>'
                     f'<animate attributeName="opacity" values=".9;0" dur="2.6s" '
                     f'repeatCount="indefinite"/></circle>'
                     f'<circle r="13" fill="none" stroke="{bg}" stroke-width="3"/>'
                     f'<circle r="7" fill="{col}"/>')
        elif st.state is StageState.CLEAR:
            o.append(f'<circle r="7" fill="#FFF" stroke="{col}" stroke-width="2.2"/>')
        else:
            o.append(f'<circle r="7" fill="{bg}" stroke="{col}" stroke-width="1.5" '
                     f'stroke-dasharray="2.5 2"/>')
        o.append(_t(0, -19, st.name, 12.5, C["ink"],
                    600 if st.state is StageState.CROSSED else 500))
    label = {StageState.CROSSED: "本次已见", StageState.CLEAR: "本次未见",
             StageState.UNKNOWN: "判不了"}[st.state]
    o.append(_t(0, 30 if st.emphasis else 22, label, 10, col, 600))
    return "".join(o) + "</g>"


def render_topology(topo: Topology) -> str:
    if not topo.tracks:
        return ""
    ty = {t.id: TOP + i * ROW_H for i, t in enumerate(topo.tracks)}
    height = TOP + len(topo.tracks) * ROW_H + 30
    s = [f'<svg viewBox="0 0 980 {height}" width="100%" role="img" '
         f'aria-label="疾病演变拓扑图" '
         f'style="display:block;max-width:980px;margin:0 auto;height:auto">',
         f'<defs><marker id="tar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" '
         f'markerHeight="5" orient="auto-start-reverse">'
         f'<path d="M0 0 L10 5 L0 10 z" fill="{C["rule"]}"/></marker>'
         f'<marker id="tarA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" '
         f'markerHeight="5" orient="auto-start-reverse">'
         f'<path d="M0 0 L10 5 L0 10 z" fill="{C["act"]}"/></marker></defs>']

    for i, ((x0, x1), lab, hint) in enumerate(ZONES):
        if i == 2:
            s.append(f'<rect x="{x0}" y="34" width="{x1-x0}" height="{height-64}" '
                     f'fill="{C["faint"]}" opacity=".55"/>')
        if i:
            s.append(f'<line x1="{x0}" y1="34" x2="{x0}" y2="{height-30}" '
                     f'stroke="{C["rule"]}" stroke-dasharray="4 4"/>')
        cx = (x0 + x1) / 2
        s += [_t(cx, 20, lab, 11.5, C["ink2"], 700), _t(cx, 33, hint, 10, C["muted"])]

    cols = {t.id: [st.col if st.col is not None else i
                   for i, st in enumerate(t.stages)] for t in topo.tracks}

    for up in topo.upstreams:
        feeds = [t for t in topo.tracks if t.upstream_id == up.id]
        if not feeds:
            continue
        uy = sum(ty[t.id] for t in feeds) / len(feeds)
        col = C["act"] if up.modifiable else C["muted"]
        bg = C["actbg"] if up.modifiable else "#FFF"
        dash = "" if up.modifiable else ' stroke-dasharray="5 3"'
        # 上游那行小字会折行，框高和下面那句注释都得跟着让位，
        # 否则第二行会压在框线和注释上（病例 3 的抗体那一串正好两行）。
        nsub = len(_wrap(up.sub, 17))
        grow = (nsub - 1) * 12
        s.append(f'<g transform="translate(102,{uy})">'
                 f'<rect x="-92" y="{-32 - grow // 2}" width="184" '
                 f'height="{64 + grow}" rx="7" fill="{bg}" '
                 f'stroke="{col}" stroke-width="1.6"{dash}/>'
                 + _t(0, -13 - grow // 2, "上游", 9.5, C["muted"], 700)
                 + _t(0, 4 - grow // 2, up.label, 13, C["ink"], 700)
                 + _tw(0, 20 - grow // 2, up.sub, 10, C["muted"], budget=17) + "</g>")
        s.append(_tw(102, uy + 46 + (grow + 1) // 2, up.note, 10, col, 600, budget=19))
        for t in feeds:
            y1, x1 = ty[t.id], COL_X[cols[t.id][0]] - 26
            if abs(y1 - uy) < 3:
                s.append(f'<line x1="196" y1="{uy}" x2="{x1}" y2="{y1}" stroke="{col}" '
                         f'stroke-width="1.4" marker-end="url(#tar)"{dash}/>')
            else:
                s.append(f'<path d="M 196 {uy} C 251 {uy}, {x1-55} {y1}, {x1} {y1}" '
                         f'fill="none" stroke="{col}" stroke-width="1.4" '
                         f'marker-end="url(#tar)"{dash}/>')

    for t in topo.tracks:
        if t.upstream_id is None:
            # 没有上游不是渲染缺失，是判读结论：本次没找到推动它的因素
            s.append(_t(102, ty[t.id] - 4, "本次未找到上游", 10.5, C["muted"], 500))
            if t.no_upstream_note:
                s.append(_tw(102, ty[t.id] + 12, t.no_upstream_note, 9.5,
                             C["muted"], budget=20))
            s.append(f'<line x1="196" y1="{ty[t.id]}" '
                     f'x2="{COL_X[cols[t.id][0]] - 26}" y2="{ty[t.id]}" '
                     f'stroke="{C["rule"]}" stroke-width="1" stroke-dasharray="2 4"/>')

    for t in topo.tracks:
        y, cs = ty[t.id], cols[t.id]
        s.append(_t(COL_X[cs[0]], y - 40, t.label, 10, C["muted"], 700))
        for i, st in enumerate(t.stages):
            x = COL_X[cs[i]]
            if i:
                px = COL_X[cs[i - 1]]
                a = px + (82 if t.stages[i - 1].emphasis else 26)
                b = x - (82 if st.emphasis else 26)
                on = st.state is StageState.CROSSED
                s.append(f'<line x1="{a}" y1="{y}" x2="{b}" y2="{y}" '
                         f'stroke="{C["act"] if on else C["rule"]}" '
                         f'stroke-width="{1.8 if on else 1.2}" '
                         f'stroke-dasharray="{"" if on else "4 4"}" '
                         f'marker-end="url({"#tarA" if on else "#tar"})"/>')
                if st.edge:
                    s.append(_t((a + b) / 2, y - 8, st.edge, 9.5,
                                C["act"] if on else C["muted"], 600))
            s.append(_node(x, y, st))
        lx = COL_X[cs[-1]] + (82 if t.stages[-1].emphasis else 26)
        s += [f'<line x1="{lx}" y1="{y}" x2="{lx+52}" y2="{y}" stroke="{C["rule"]}" '
              f'stroke-dasharray="2 4"/>',
              _t(lx + 68, y + 4, "…", 17, C["rule"], 700),
              _t(lx + 68, y + 22, "不展开", 9, C["muted"])]

    ly, x = height - 14, 214
    for st, lb in ((StageState.CROSSED, "本次已见"),
                   (StageState.CLEAR, "本次未见（有指标判定）"),
                   (StageState.UNKNOWN, "判不了（缺指标）")):
        col = {StageState.CROSSED: C["act"], StageState.CLEAR: C["settle"],
               StageState.UNKNOWN: C["muted"]}[st]
        if st is StageState.CROSSED:
            s.append(f'<circle cx="{x}" cy="{ly-4}" r="5" fill="{col}"/>')
        elif st is StageState.CLEAR:
            s.append(f'<circle cx="{x}" cy="{ly-4}" r="5" fill="#FFF" stroke="{col}" '
                     f'stroke-width="2"/>')
        else:
            s.append(f'<circle cx="{x}" cy="{ly-4}" r="5" fill="{C["faint"]}" '
                     f'stroke="{col}" stroke-dasharray="2 2"/>')
        s.append(_t(x + 11, ly, lb, 10.5, C["muted"], anchor="start"))
        x += len(lb) * 11 + 44
    return "".join(s) + "</svg>"
