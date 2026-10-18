"""Build mobile-first HTML pages from the project's Markdown docs.

Usage:  python tools/build_docs.py
Needs:  pip install markdown
Output: site/  (open site/index.html)
"""
from __future__ import annotations

import datetime as dt
import html
import re
import shutil
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("Missing package. Run:  pip install markdown")

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

# (source, output, short title, accent token)
PAGES = [
    ("README.md", "index.html", "الرئيسية", "primary-text"),
    ("docs/OVERVIEW.md", "overview.html", "في دقيقتين", "primary-text"),
    ("docs/PRODUCT.md", "product.html", "المنتج", "primary-text"),
    ("docs/ROADMAP.md", "roadmap.html", "خارطة البناء", "ok"),
    ("docs/ARCHITECTURE.md", "architecture.html", "التصميم التقني", "other"),
    ("docs/DOMAIN.md", "domain.html", "علم الري", "rain"),
    ("docs/MARKET.md", "market.html", "السوق والمنافسين", "warn"),
    ("docs/JOURNEY.md", "journey.html", "رحلة المشروع", "ok"),
    ("reference-cases/README.md", "reference-cases.html", "الحالات المرجعية", "rain"),
]
EXTRA_DIRS = ["design", "research"]
STANDALONE = {"overview.html"}
EXTRA_TITLES = {
    "IRRIGATION_Competitor_Study.html": ("دراسة المنافسين", "المنافسين في مصر وبرا، بالتفصيل"),
    "IRRIGATION_Color_System.html": ("نظام الألوان", "ألوان الواجهة والرسوم وأكوادها"),
    "IRRIGATION_Mind_Map.html": ("خريطة التطبيق", "الشاشات والتنقل ورحلة العرض، مقترح"),
}  # pages meant to be shared alone: no cross-page links  # standalone HTML pages copied as-is

DESCRIPTIONS = {
    "overview.html": "تعريف بسيط للفريق والمشرفين، ينفع يتبعت لوحده",
    "product.html": "بنبني إيه ولمين وليه هيختارونا",
    "roadmap.html": "ترتيب البناء وخطوات كل إصدار",
    "architecture.html": "بنبني المنصة إزاي",
    "domain.html": "المفاهيم والمعادلات والمصطلحات",
    "market.html": "المنافسين والعملاء والمقابلات",
    "journey.html": "القرارات والمشاكل واليوميات",
    "reference-cases.html": "حالات اختبار الحسابات",
}

CALLOUTS = {"قاعدة": "rule", "للبحث": "research", "مقترح": "proposal", "ملحوظة": "note", "تحذير": "research"}


STATUS = {"done": "تم", "doing": "شغال", "next": "الجاي", "todo": "لسه"}


def roadmap_status() -> dict[str, str]:
    """Read '<!-- status: V0=next V1=done -->' from ROADMAP.md; default todo."""
    text = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
    m = re.search(r"<!--\s*status:(.*?)-->", text, flags=re.S)
    found = dict(re.findall(r"(V\d+)=(done|doing|next)", m.group(1))) if m else {}
    vers = re.findall(r"^### (V\d+) ·", text, flags=re.M)
    return {v: found.get(v, "todo") for v in vers}


def progress_block() -> str:
    st = roadmap_status()
    if not st:
        return ""
    done = sum(1 for v in st.values() if v == "done")
    cur = next((v for v, s_ in st.items() if s_ in ("doing", "next")), None)
    j = (ROOT / "docs/JOURNEY.md").read_text(encoding="utf-8")
    decs = re.findall(r"^### (قرار رقم \d+): (.+)$", j, flags=re.M)
    last = f"{decs[-1][0]}: {decs[-1][1]}" if decs else "—"
    cells = "".join(f'<i class="s-{s_}" title="{v} · {STATUS[s_]}"></i>' for v, s_ in st.items())
    return (f'<section class="now"><div class="now-h"><b>وصلنا فين</b><span>{done} من {len(st)} إصدار خلصوا</span></div>'
            f'<div class="strip">{cells}</div>'
            f'<div class="now-r"><span>الإصدار الحالي</span><b dir="ltr">{cur or "—"}</b></div>'
            f'<div class="now-r"><span>آخر قرار</span><b>{html.escape(last)}</b></div></section>')


def legend_html() -> str:
    return ('<div class="legend"><span style="--c:var(--primary-text)">الفكرة</span><span style="--c:var(--ok)">التقدم</span>'
            '<span style="--c:var(--other)">التقنية</span><span style="--c:var(--rain)">العلم</span><span style="--c:var(--warn)">السوق</span></div>')


def extra_pages() -> list[tuple[str, str, str]]:
    """(href from site root, title, description) for standalone pages in EXTRA_DIRS."""
    out = []
    for d in EXTRA_DIRS:
        for p in sorted((ROOT / d).glob("*.html")) if (ROOT / d).exists() else []:
            t, desc = EXTRA_TITLES.get(p.name, (p.stem.replace("_", " "), "صفحة عرض"))
            out.append((f"{d}/{p.name}", t, desc))
    return out


def link_map() -> dict[str, str]:
    return {Path(src).as_posix(): out for src, out, _, _ in PAGES}


def fix_links(body: str, src: str, links: dict[str, str]) -> str:
    base = Path(src).parent

    def repl(m: re.Match) -> str:
        target = m.group(1)
        if target.startswith(("http://", "https://", "#")):
            return m.group(0)
        resolved = (base / target).as_posix()
        parts = []
        for p in resolved.split("/"):
            if p == "..":
                if parts:
                    parts.pop()
            elif p and p != ".":
                parts.append(p)
        key = "/".join(parts)
        return f'href="{links.get(key, target)}"'

    return re.sub(r'href="([^"]+\.md)"', repl, body)


def style_callouts(body: str) -> str:
    def repl(m: re.Match) -> str:
        inner = m.group(1)
        kind = "lead"
        first = re.search(r"<strong>([^<:]+):?</strong>", inner)
        if first:
            for word, cls in CALLOUTS.items():
                if first.group(1).strip().startswith(word):
                    kind = cls
                    break
        return f'<div class="callout {kind}">{inner}</div>'

    return re.sub(r"<blockquote>\s*(.*?)\s*</blockquote>", repl, body, flags=re.S)


def style_steps(body: str) -> str:
    body = body.replace("← <strong>خالصة لما:</strong>", '<br><span class="done">خالصة لما:</span>')
    return body


def wrap_tables(body: str) -> str:
    return re.sub(r"(<table>.*?</table>)", r'<div class="scroll">\1</div>', body, flags=re.S)


def collapse_h3(body: str) -> str:
    """Turn each h3 section into a <details> card."""
    parts = re.split(r"(<h[23][^>]*>.*?</h[23]>)", body, flags=re.S)
    out, open_card = [], False
    for part in parts:
        h = re.match(r"<h([23])([^>]*)>(.*?)</h[23]>", part, flags=re.S)
        if h and open_card:
            out.append("</div></details>")
            open_card = False
        if h and h.group(1) == "3":
            attrs, text = h.group(2), h.group(3)
            id_attr = re.search(r'id="([^"]+)"', attrs)
            ident = f' id="{id_attr.group(1)}"' if id_attr else ""
            label = re.sub(r"<[^>]+>", "", text)
            head, _, tail = label.partition("·")
            title = (
                f'<span class="tag">{head.strip()}</span><span class="t">{tail.strip()}</span>'
                if tail else f'<span class="t">{label.strip()}</span>'
            )
            out.append(f'<details class="card"{ident}><summary>{title}<span class="chev" aria-hidden="true">⌄</span></summary><div class="card-body">')
            open_card = True
        else:
            out.append(part)
    if open_card:
        out.append("</div></details>")
    return "".join(out)


def page_toc(md: markdown.Markdown) -> list[tuple[str, str]]:
    return [(t["id"], t["name"]) for t in md.toc_tokens[0]["children"]] if md.toc_tokens else []


def render(src: str, out: str, title: str, accent: str, links: dict[str, str], built: str) -> str:
    text = (ROOT / src).read_text(encoding="utf-8")
    collapse = "<!-- collapse-h3 -->" in text
    text = re.sub(r'^\s*<div dir="rtl">\s*|\s*</div>\s*$', "", text)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"],
                           extension_configs={"toc": {"slugify": slug}})
    body = md.convert(text)
    toc = page_toc(md)

    # split title + lead out of the body
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, flags=re.S)
    page_title = h1.group(1) if h1 else title
    body = re.sub(r"<h1[^>]*>.*?</h1>", "", body, count=1, flags=re.S)
    lead = ""
    m = re.match(r"\s*<blockquote>\s*(.*?)\s*</blockquote>", body, flags=re.S)
    if m:
        lead = f'<div class="lead">{m.group(1)}</div>'
        body = body[m.end():]

    body = fix_links(body, src, links)
    lead = fix_links(lead, src, links)
    body = style_callouts(body)
    body = style_steps(body)
    body = wrap_tables(body)
    body = body.replace("<pre>", '<pre dir="ltr">')
    if collapse:
        body = collapse_h3(body)
        if src == "docs/ROADMAP.md":
            st = roadmap_status()
            body = re.sub(r'(<span class="tag">(V\d+)</span><span class="t">.*?</span>)(<span class="chev")',
                          lambda m: f'{m.group(1)}<span class="st s-{st.get(m.group(2), "todo")}">{STATUS[st.get(m.group(2), "todo")]}</span>{m.group(3)}', body, flags=re.S)

    cards = ""
    if out == "index.html":
        # the cards below replace the README's file table
        body = re.sub(r'<h2 id="ملفات-المشروع">.*?(?=<h2)', "", body, count=1, flags=re.S)
        toc = []
        items = "".join(
            f'<a class="doc" href="{o}" style="--c:var(--{a})"><span class="n">{i:02d}</span><b>{t}</b><span class="d">{DESCRIPTIONS.get(o, "")}</span></a>'
            for i, (_, o, t, a) in enumerate(PAGES[1:], 1)
        )
        extras = "".join(
            f'<a class="doc" href="{h}" style="--c:var(--muted)"><span class="n">↗</span><b>{t}</b><span class="d">{d}</span></a>'
            for h, t, d in extra_pages()
        )
        cards = (progress_block() + '<h2 class="sec">ملفات المشروع</h2>' + legend_html()
                 + f'<nav class="docs" aria-label="ملفات المشروع">{items}</nav>'
                 + f'<h2 class="sec">صفحات العرض</h2><nav class="docs" aria-label="صفحات العرض">{extras}</nav>')

    toc_html = ""
    if len(toc) > 2:
        lis = "".join(f'<a href="#{i}">{n}</a>' for i, n in toc)
        toc_html = f'<details class="toc"><summary>في الصفحة دي</summary><nav>{lis}</nav></details>'

    idx = [o for _, o, _, _ in PAGES].index(out)
    prev_l = PAGES[idx - 1] if idx > 0 else None
    next_l = PAGES[idx + 1] if idx + 1 < len(PAGES) else None
    pager = '<nav class="pager">'
    pager += f'<a href="{prev_l[1]}"><small>السابق</small>{prev_l[2]}</a>' if prev_l else "<span></span>"
    pager += f'<a class="next" href="{next_l[1]}"><small>التالي</small>{next_l[2]}</a>' if next_l else "<span></span>"
    pager += "</nav>"

    current = ' aria-current="page"'
    menu = '<p class="grp">الملفات</p>' + "".join(
        f'<a href="{o}"{current if o == out else ""} style="--c:var(--{a})">{t}</a>'
        for _, o, t, a in PAGES
    ) + '<p class="grp">صفحات العرض</p>' + "".join(
        f'<a href="{h}" style="--c:var(--muted)">{t}<span aria-hidden="true">↗</span></a>' for h, t, _ in extra_pages()
    )
    tools = "" if collapse is False else '<div class="tools"><button type="button" data-all="1">افتح الكل</button><button type="button" data-all="0">اقفل الكل</button></div>'

    return TEMPLATE.format(
        title=html.escape(re.sub(r"<[^>]+>", "", page_title)), page_title=page_title, short=title,
        accent=accent, lead=lead, cards=cards, toc=toc_html, tools=tools, body=body,
        menu=menu, pager=pager, src=src, built=built, css=CSS.strip(), body_class="standalone" if out in STANDALONE else "",
    )


def slug(value: str, separator: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[^\w؀-ۿ\s-]", "", value).strip().lower()
    return re.sub(r"[\s_-]+", separator, value)


TEMPLATE = """<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0B0B0D">
<title>{title} · Smart Irrigation System</title>
<link rel="icon" href="design/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body class="{body_class}" style="--accent:var(--{accent})">
<div class="progress" aria-hidden="true"><i id="progress"></i></div>
<header class="bar">
  <a class="brand" href="index.html"><img src="design/logo-mark-white.png" alt="" width="26" height="26"><span>Smart <b>Irrigation</b></span></a>
  <span class="here">{short}</span>
  <button class="menu-btn" type="button" aria-controls="nav" aria-expanded="false" aria-label="كل الصفحات"><span></span></button>
</header>
<div class="layout">
<nav id="nav" class="side" aria-label="صفحات المشروع">{menu}</nav>
<div class="scrim" hidden></div>
<main class="page">
  <h1>{page_title}</h1>
  {lead}
  {cards}
  {toc}
  {tools}
  <article class="content">{body}</article>
  {pager}
  <footer>اتعملت من <code>{src}</code> · {built}</footer>
</main>
</div>
<script>
const nav=document.getElementById('nav'),btn=document.querySelector('.menu-btn'),scrim=document.querySelector('.scrim');
function setNav(o){{document.body.classList.toggle('nav-open',o);btn.setAttribute('aria-expanded',o);scrim.hidden=!o;}}
btn.addEventListener('click',()=>setNav(!document.body.classList.contains('nav-open')));
scrim.addEventListener('click',()=>setNav(false));
document.addEventListener('keydown',e=>{{if(e.key==='Escape')setNav(false)}});
document.querySelectorAll('[data-all]').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelectorAll('details.card').forEach(d=>d.open=b.dataset.all==='1');
}}));
function openHash(){{const id=decodeURIComponent(location.hash.slice(1));const el=id&&document.getElementById(id);
  if(el){{const d=el.closest('details');if(d)d.open=true;}}}}
window.addEventListener('hashchange',openHash);openHash();
document.querySelectorAll('.toc a').forEach(a=>a.addEventListener('click',()=>{{const d=a.closest('details');if(d)d.open=false;}}));
const pr=document.getElementById('progress');
function prog(){{const h=document.documentElement;const m=h.scrollHeight-h.clientHeight;pr.style.transform='scaleX('+(m>0?h.scrollTop/m:0)+')';}}
document.addEventListener('scroll',prog,{{passive:true}});prog();
</script>
</body>
</html>
"""

CSS = """
:root{
  color-scheme:dark;
  --bg:#0B0B0D; --card:#141416; --raised:#1C1C1F; --border:#232327; --border-strong:#34343A;
  --text:#F2F2F3; --soft:#C4C4C8; --muted:#8E8E94;
  --primary:#0B5FE8; --primary-text:#3D86FF;
  --ok:#34B27B; --warn:#E0B04A; --danger:#E5706E; --rain:#30C3D9; --other:#A97CF5;
  --radius:14px; --bar:56px;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-padding-top:calc(var(--bar) + 12px)}
body{margin:0;background:var(--bg);color:var(--text);font:400 16px/1.8 Cairo,Tahoma,Arial,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--primary-text);text-underline-offset:3px}
code{direction:ltr;unicode-bidi:isolate;font-family:ui-monospace,Consolas,monospace;font-size:.85em;background:var(--raised);border:1px solid var(--border);padding:0 6px;border-radius:6px}
pre{direction:ltr;text-align:left;overflow-x:auto;background:#09090B;border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin:14px 0;font-size:13px;line-height:1.7}
pre code{background:none;border:0;padding:0;font-size:inherit}
:focus-visible{outline:2px solid var(--primary-text);outline-offset:2px;border-radius:6px}

/* progress */
.progress{position:fixed;inset:0 0 auto 0;height:2px;z-index:30;pointer-events:none}
.progress i{display:block;height:100%;background:var(--primary-text);transform-origin:right;transform:scaleX(0)}

/* top bar */
.bar{position:sticky;top:0;z-index:20;height:calc(var(--bar) + env(safe-area-inset-top,0px));display:flex;align-items:center;gap:12px;
  background:rgba(11,11,13,.86);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);
  padding:env(safe-area-inset-top,0px) max(16px,env(safe-area-inset-right,0px)) 0 max(16px,env(safe-area-inset-left,0px))}
.brand{display:flex;align-items:center;gap:9px;font-weight:800;color:var(--text);text-decoration:none;direction:ltr;white-space:nowrap}
.brand b{color:var(--primary-text);font-weight:800}
.here{color:var(--muted);font-size:14px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.here::before{content:"/";margin-inline-end:10px;color:var(--border-strong)}
.menu-btn{width:42px;height:42px;border-radius:12px;border:1px solid var(--border);background:var(--card);cursor:pointer;display:grid;place-items:center;flex:none}
.menu-btn span,.menu-btn span::before,.menu-btn span::after{display:block;width:18px;height:2px;border-radius:2px;background:var(--text);position:relative;transition:transform .2s,background .2s}
.menu-btn span::before,.menu-btn span::after{content:"";position:absolute;inset-inline-start:0}
.menu-btn span::before{top:-6px}.menu-btn span::after{top:6px}
.nav-open .menu-btn span{background:transparent}
.nav-open .menu-btn span::before{transform:translateY(6px) rotate(45deg)}
.nav-open .menu-btn span::after{transform:translateY(-6px) rotate(-45deg)}

/* side nav (drawer on mobile, sidebar on desktop) */
.side{position:fixed;z-index:19;top:calc(var(--bar) + env(safe-area-inset-top,0px));bottom:0;right:0;width:min(300px,86vw);
  background:var(--card);border-left:1px solid var(--border);padding:12px 10px calc(24px + env(safe-area-inset-bottom,0px));overflow-y:auto;
  transform:translateX(100%);transition:transform .22s ease,visibility .22s;visibility:hidden}
.nav-open .side{transform:none;visibility:visible}
.scrim{position:fixed;inset:0;z-index:18;background:rgba(0,0,0,.55)}
.side .grp{margin:14px 10px 6px;font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.2px}
.side .grp:first-child{margin-top:4px}
.side a{display:flex;align-items:center;gap:10px;color:var(--soft);text-decoration:none;padding:9px 12px;border-radius:10px;font-size:15px}
.side a::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--c);flex:none}
.side a span{margin-inline-start:auto;color:var(--muted);font-size:13px}
.side a:hover{background:var(--raised);color:var(--text)}
.side a[aria-current]{background:var(--raised);color:var(--text);font-weight:700}

/* page */
.page{max-width:720px;margin:0 auto;padding:28px max(16px,env(safe-area-inset-right,0px)) calc(48px + env(safe-area-inset-bottom,0px)) max(16px,env(safe-area-inset-left,0px));min-width:0}
h1{font-size:30px;font-weight:800;line-height:1.35;margin:0 0 12px;letter-spacing:-.2px}
h1::before{content:"";display:block;width:36px;height:4px;border-radius:4px;background:var(--accent);margin-bottom:14px}
h1 code{background:none;border:0;padding:0;font-size:1em;font-family:inherit}
.lead{color:var(--soft);font-size:17px;line-height:1.85;margin-bottom:18px}
.lead p{margin:0}
.content{min-width:0}
.content h2{font-size:22px;font-weight:800;margin:44px 0 12px;padding-top:18px;border-top:1px solid var(--border)}
.content>h2:first-child{margin-top:12px;border-top:0;padding-top:0}
.content h3{font-size:17px;font-weight:700;margin:24px 0 8px}
.content p{margin:12px 0}
.content ul,.content ol{padding-inline-start:22px;margin:10px 0;display:grid;gap:8px}
.content li::marker{color:var(--muted)}
.content li p{margin:0}
.content strong{color:var(--text);font-weight:700}
.content hr{border:0;border-top:1px solid var(--border);margin:28px 0}
h2.sec{font-size:18px;font-weight:800;margin:30px 0 10px}

/* home */
.docs{display:grid;gap:10px;margin:0 0 8px}
.doc{position:relative;display:grid;grid-template-columns:auto 1fr;column-gap:12px;align-items:center;text-decoration:none;color:var(--text);
  background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;transition:border-color .15s,background .15s}
.doc:hover{border-color:var(--border-strong);background:#17171A}
.doc .n{grid-row:span 2;width:36px;height:36px;border-radius:10px;display:grid;place-items:center;font-size:13px;font-weight:800;color:var(--c);
  background:color-mix(in srgb,var(--c) 14%,transparent);direction:ltr}
.doc b{font-size:16px}
.doc .d{color:var(--muted);font-size:14px;line-height:1.6}
.now{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin:4px 0 6px;display:grid;gap:12px}
.now-h{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.now-h b{font-size:16px}
.now-h span{color:var(--muted);font-size:14px}
.strip{display:grid;grid-template-columns:repeat(17,1fr);gap:3px}
.strip i{height:10px;border-radius:3px;background:var(--raised)}
.strip i.s-done{background:var(--ok)} .strip i.s-doing{background:var(--primary-text)} .strip i.s-next{background:var(--warn)}
.now-r{display:flex;justify-content:space-between;gap:12px;font-size:15px;border-top:1px solid var(--border);padding-top:10px}
.now-r span{color:var(--muted);flex:none}
.now-r b{text-align:end;font-weight:700}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin:0 0 12px;font-size:13px;color:var(--muted)}
.legend span::before{content:"";display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--c);margin-inline-end:6px}

/* toc */
.toc{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);margin:12px 0 8px}
.toc summary{cursor:pointer;padding:12px 16px;font-weight:700;list-style:none;display:flex;justify-content:space-between;align-items:center}
.toc summary::-webkit-details-marker{display:none}
.toc summary::after{content:"";width:8px;height:8px;border:solid var(--muted);border-width:0 2px 2px 0;transform:rotate(45deg);margin-top:-4px;transition:transform .15s}
.toc[open] summary::after{transform:rotate(-135deg);margin-top:4px}
.toc nav{display:grid;padding:0 8px 10px}
.toc nav a{color:var(--soft);text-decoration:none;padding:7px 10px;border-radius:8px;font-size:15px}
.toc nav a:hover{background:var(--raised);color:var(--text)}

/* tables */
.scroll{overflow-x:auto;margin:14px 0;border:1px solid var(--border);border-radius:12px;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:14.5px;background:var(--card)}
th,td{padding:10px 12px;text-align:start;vertical-align:top;border-bottom:1px solid var(--border);min-width:100px}
th{background:var(--raised);font-weight:700;white-space:nowrap;color:var(--soft);font-size:13.5px}
tr:last-child td{border-bottom:0}
tbody tr:hover td{background:#17171A}

/* callouts */
.callout{border-radius:12px;padding:12px 16px;margin:14px 0;background:color-mix(in srgb,var(--c,var(--primary-text)) 8%,var(--card));border:1px solid color-mix(in srgb,var(--c,var(--primary-text)) 28%,transparent);font-size:15px}
.callout p{margin:0}
.callout>p+p{margin-top:6px}
.callout strong:first-child{color:var(--c,var(--primary-text))}
.callout.rule{--c:var(--ok)} .callout.research{--c:var(--warn)} .callout.proposal{--c:var(--other)} .callout.note{--c:var(--primary-text)}

/* collapsible cards */
.tools{display:flex;gap:8px;margin:16px 0 6px}
.tools button{font:inherit;font-size:14px;font-weight:600;color:var(--soft);background:var(--card);border:1px solid var(--border);border-radius:10px;padding:6px 14px;cursor:pointer}
.tools button:hover{color:var(--text);border-color:var(--border-strong)}
details.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);margin:10px 0;transition:border-color .15s}
details.card[open]{border-color:var(--border-strong)}
details.card summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:14px 16px;min-height:52px}
details.card summary::-webkit-details-marker{display:none}
details.card .tag{direction:ltr;font-weight:800;color:var(--accent);background:color-mix(in srgb,var(--accent) 14%,transparent);border-radius:7px;padding:1px 8px;font-size:13.5px;flex:none}
details.card .t{font-weight:700;flex:1;line-height:1.5}
details.card .chev{width:8px;height:8px;border:solid var(--muted);border-width:0 2px 2px 0;transform:rotate(45deg);margin-top:-4px;transition:transform .15s;font-size:0;flex:none}
details.card[open] .chev{transform:rotate(-135deg);margin-top:4px}
.card-body{padding:2px 16px 14px;border-top:1px solid var(--border)}
.st{flex:none;font-size:12px;font-weight:700;border-radius:999px;padding:0 9px;line-height:22px;background:var(--raised);color:var(--muted)}
.st.s-done{background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)}
.st.s-doing{background:color-mix(in srgb,var(--primary-text) 18%,transparent);color:var(--primary-text)}
.st.s-next{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.done{color:var(--ok);font-size:14px;font-weight:700}
.done::before{content:"✓ "}

/* pager + footer */
.pager{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:44px}
.pager a{display:grid;gap:2px;text-decoration:none;color:var(--text);background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:12px 16px;font-weight:700}
.pager a:hover{border-color:var(--border-strong)}
.pager a small{color:var(--muted);font-weight:400;font-size:13px}
.pager a.next{text-align:end}
footer{margin-top:26px;color:var(--muted);font-size:13px}

.standalone .menu-btn,.standalone .side,.standalone .pager,.standalone footer{display:none}
@media (min-width:720px){
  h1{font-size:36px}
  .docs{grid-template-columns:1fr 1fr}
}
@media (min-width:1080px){
  .menu-btn{display:none}
  .layout{display:grid;grid-template-columns:260px minmax(0,1fr)}
  .side{position:sticky;top:calc(var(--bar) + env(safe-area-inset-top,0px));height:calc(100vh - var(--bar));width:auto;transform:none;visibility:visible;
    background:transparent;border-left:1px solid var(--border)}
  .scrim{display:none}
  .standalone .layout{display:block}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""


V5 = ("--bg:#0B0B0D; --card:#141416; --raised:#1C1C1F; --border:#232327;\n"
      "  --text:#F2F2F3; --muted:#8E8E94; --soft:#C4C4C8;\n"
      "  --primary:#0B5FE8; --primary-text:#3D86FF;\n"
      "  --ok:#34B27B; --warn:#E0B04A; --danger:#E5706E; --rain:#30C3D9; --other:#A97CF5;")
BACK = ('<a href="../index.html" style="position:fixed;bottom:calc(16px + env(safe-area-inset-bottom,0px));left:16px;z-index:50;box-shadow:0 8px 24px rgba(0,0,0,.45);display:inline-flex;align-items:center;gap:8px;'
        'background:rgba(20,20,22,.9);color:#F2F2F3;border:1px solid #34343A;border-radius:12px;padding:6px 12px 6px 10px;'
        'font:700 14px Cairo,Tahoma,sans-serif;text-decoration:none;-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)">'
        '<img src="../design/logo-mark-white.png" alt="" width="18" height="18">كل الصفحات</a>')


def polish_extra(page: str) -> str:
    """Give copied standalone pages the v5 palette and a way back home."""
    page = re.sub(r"--bg:#18191B;.*?--other:#9646EF;", V5, page, count=1, flags=re.S)
    page = page.replace("IRRIGATION —", "Smart Irrigation —")
    if "<!-- si-back -->" not in page:
        page = re.sub(r"(<body[^>]*>)", r"\1<!-- si-back -->" + BACK.replace("\\", "\\\\"), page, count=1)
    if 'rel="icon"' not in page:
        page = page.replace("</title>", '</title>\n<link rel="icon" href="../design/favicon.png">', 1)
    return page


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    links = link_map()
    built = dt.date.today().isoformat()
    for src, out, title, accent in PAGES:
        if not (ROOT / src).exists():
            print(f"skip (missing): {src}")
            continue
        (SITE / out).write_text(render(src, out, title, accent, links, built), encoding="utf-8")
        print(f"built: site/{out}")
    for d in EXTRA_DIRS:
        if (ROOT / d).exists():
            shutil.copytree(ROOT / d, SITE / d)
            for page in (SITE / d).glob("*.html"):
                page.write_text(polish_extra(page.read_text(encoding="utf-8")), encoding="utf-8")
            print(f"copied: site/{d}/")


if __name__ == "__main__":
    main()
