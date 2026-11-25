"""Code-drawn, offline comparison sheets for the conversational design wizard.

HTML generation and integrity checks use only the standard library. Rasterizing
the reviewed HTML is an optional maintainer task using Playwright, not inference.
"""
import hashlib
from html import escape
import json
from pathlib import Path
import struct

from .uiux import ROOT, load_uiux_flow, question_choices, read_json, sample_path

CSS = """
*{box-sizing:border-box}body{margin:0;background:#eef1f7;color:#17243b;font-family:Arial,sans-serif}
main{width:1200px;padding:40px}header{margin-bottom:26px}.eyebrow{color:#505ac6;font-size:14px;font-weight:700;letter-spacing:2px}
h1{font-size:32px;line-height:1.2;margin:10px 0}header p,footer{font-size:16px;line-height:1.5;color:#526078;margin:0}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.grid.three{grid-template-columns:repeat(3,minmax(0,1fr))}
.grid.one{grid-template-columns:1fr}.option{min-width:0;background:#fff;border:1px solid #d8dfec;border-radius:18px;overflow:hidden}
.caption{padding:16px 18px;display:flex;align-items:center;gap:12px;border-bottom:1px solid #e6eaf2;min-height:65px}
.code{flex:0 0 32px;height:32px;border-radius:10px;display:grid;place-items:center;background:#e9edff;color:#3546a5;font-size:17px;font-weight:700}
h2{font-size:19px;line-height:1.3;margin:0}.detail{font-size:14px;line-height:1.45;color:#526078;padding:12px 18px 16px;min-height:48px}
.preview{height:230px;position:relative;overflow:hidden;background:#f4f6fb;padding:16px}.preview>div{height:100%}footer{margin-top:24px}
.mini{--bg:#f4f6fb;--surface:#fff;--ink:#19283f;--muted:#63718a;--accent:#4f57ce;--line:#dce2ed;--radius:10px;background:var(--bg);color:var(--ink);display:flex;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;font-size:12px}
.mini nav{width:86px;flex-shrink:0;background:var(--surface);border-right:1px solid var(--line);padding:14px 10px;display:flex;flex-direction:column;gap:10px}
.mini .brand{font-weight:700;color:var(--accent);margin-bottom:8px;letter-spacing:.5px}.mini nav span{color:var(--muted)}.mini nav .active{color:var(--accent);font-weight:700}
.mini section{flex:1;min-width:0;padding:15px}.mini .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;gap:8px}
.mini strong{font-size:17px}.button{display:inline-block;background:var(--accent);color:#fff;border-radius:var(--radius);padding:7px 10px;font-size:11px;white-space:nowrap}
.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.stat{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:10px;box-shadow:var(--shadow,none)}
.stat small{font-size:10px;color:var(--muted)}.stat b{display:block;font-size:21px;margin-top:4px}.activity{margin-top:10px;background:var(--surface);border-radius:var(--radius);border:1px solid var(--line);padding:10px}
.activity .line{display:flex;justify-content:space-between;gap:6px;font-size:11px}.activity .bar{height:5px;margin-top:8px;border-radius:3px;background:var(--line)}.activity .bar i{display:block;width:72%;height:100%;background:var(--accent);border-radius:3px}
.style-minimal{--bg:#fff;--line:#eceef3;--accent:#242d3b}.style-minimal .stat{border:0;padding-left:0}.style-minimal nav{border:0}
.style-bento{--bg:#edeefb;--accent:#5b4bc5;--radius:19px}.style-bento .stat:first-child{background:#ded8ff}.style-bento .stat:last-child{background:#e8f7d9}.style-bento .stat{border:0}.style-bento .activity{border:0}
.style-matte-glass{--bg:linear-gradient(120deg,#a9c0d7,#d6c8eb);--surface:#f8faffde;--line:#ffffffc9;--accent:#4d5c98;backdrop-filter:blur(10px)}
.style-apple-inspired{--bg:#edf0f5;--accent:#1971d4;--line:#e0e4eb}.style-apple-inspired nav{background:#e7eaf0}.style-apple-inspired .stat{border:0}
.style-material-design{--bg:#f4effc;--surface:#fffaff;--accent:#6750a4;--line:#e5dcef}.style-material-design .button{border-radius:24px}.style-material-design .stat{border:0;box-shadow:0 3px 5px #21113720}
.style-corporate{--bg:#f2f5f8;--accent:#21547a;--line:#d1dce6}.style-corporate nav{background:#1c3552}.style-corporate nav span{color:#d7e1eb}.style-corporate .brand,.style-corporate nav .active{color:#fff}
.style-futuristic{--bg:#0b1b2e;--surface:#11283d;--ink:#e0f8ff;--muted:#a3c2d4;--accent:#2580a0;--line:#28617a;font-family:Consolas,monospace}.style-futuristic .brand,.style-futuristic nav .active{color:#78d8ef}
.style-luxury{--bg:#201f1d;--surface:#2e2b26;--ink:#f8f0dd;--muted:#d1c6ae;--accent:#a4874a;--line:#625539;font-family:Georgia,serif}.style-luxury .brand,.style-luxury nav .active{color:#e6ca8e}.style-luxury strong{letter-spacing:1px}
.style-fluent-design{--bg:#e8eff6;--accent:#1768a6;--surface:#ffffffd9}.style-fluent-design nav{background:#e0eaf4}
.style-linux-inspired{--bg:#f1efec;--accent:#a64613;--line:#b9b7b2}.style-linux-inspired nav{background:#e0ddda}.style-linux-inspired .stat{padding:7px}
.style-glassmorphism{--bg:linear-gradient(130deg,#8295d2,#c6b3e6 50%,#90d4dc);--surface:#ffffffb8;--accent:#3d4a94;--line:#ffffffb0}
.style-neumorphism{--bg:#e4e9ef;--surface:#e4e9ef;--line:#c4ced9;--accent:#3f5a91}.style-neumorphism .stat{box-shadow:5px 5px 9px #bec6d0,-5px -5px 9px #fff}
.style-brutalism{--bg:#fcf5c7;--accent:#343448;--line:#252a35}.style-brutalism .stat{border:2px solid #252a35;box-shadow:3px 3px 0 #252a35}.style-brutalism .button{background:#6b48d3}
.style-flat{--bg:#edf5f4;--accent:#14796c;--line:#cbe2df}.style-flat .stat{background:#d7eeeb;border:0}
.style-retro{--bg:#f4e8cd;--surface:#fff3da;--accent:#9f462e;--line:#a28b67}.style-retro .stat{box-shadow:2px 2px 0 #7d674b}
.style-cyberpunk{--bg:#130f26;--surface:#231b3a;--ink:#f2efff;--muted:#c2b4d7;--accent:#8955bf;--line:#685486;font-family:Consolas,monospace}.style-cyberpunk .brand,.style-cyberpunk nav .active{color:#f3d673}
.style-editorial{--bg:#faf8f2;--accent:#4f483d;--line:#c9c0ae}.style-editorial nav{display:none}.style-editorial strong{font-family:Georgia,serif;font-size:25px}.style-editorial .stat{border:0;border-top:1px solid var(--line)}
.style-monochrome{--bg:#eee;--surface:#fafafa;--accent:#343434;--ink:#202020;--line:#ccc}.style-industrial{--bg:#e6e7e6;--accent:#4f5b55;--line:#717e78;font-family:Consolas,monospace}
.style-custom{--bg:linear-gradient(130deg,#e3f6f1,#f6e6fb);--accent:#7456b1;--line:#c2cfdf}
.theme-dark{--bg:#101a2b;--surface:#1c2a41;--ink:#eef3ff;--muted:#b6c3d8;--line:#354662;--accent:#566cce}
.theme-dark .brand,.theme-dark nav .active{color:#a7bdff}
.system-pair{display:flex;gap:6px}.system-pair .mini{flex:1}.system-pair nav{display:none}.system-pair .mini section{padding:10px}.system-pair .stats{grid-template-columns:1fr}.system-pair .stat:last-child,.system-pair .button{display:none}
.swatches{display:flex;height:70px!important;border-radius:8px;overflow:hidden}.swatches span{flex:1}.palette-ui{margin-top:12px;display:flex;align-items:center;justify-content:space-between;padding:18px;border-radius:10px;font-size:16px;font-weight:700}.hexes{display:flex;justify-content:space-between;font:11px Consolas,monospace;margin-top:8px}
.nav-right{flex-direction:row-reverse}.nav-right nav{border-right:0;border-left:1px solid var(--line)}.nav-top,.nav-bottom{flex-direction:column}.nav-top nav,.nav-bottom nav{flex-direction:row;width:auto;padding:10px;gap:16px;align-items:center;border:0}.nav-top nav .brand,.nav-bottom nav .brand{margin:0}.nav-bottom{flex-direction:column-reverse}.nav-bottom section,.nav-top section{padding:10px}.nav-bottom .activity,.nav-top .activity{display:none}
.nav-floating{padding:9px;gap:8px}.nav-floating nav{border:1px solid var(--line);border-radius:12px;box-shadow:0 4px 12px #26394f16}.nav-floating section{padding:6px}.mini aside{width:55px;border-left:1px solid var(--line);padding:14px 8px;background:#e9edf7;font-size:10px;line-height:2;color:#566780}
.nav-centered nav{display:none}.nav-centered section{max-width:300px;margin:auto}.nav-centered .top{justify-content:center}.nav-bento nav{display:none}.nav-bento .stats{grid-template-columns:2fr 1fr}.nav-bento .stat:first-child{background:#e5e0ff}.nav-bento .activity{width:75%;background:#e4f2e5}
.density{height:100%;background:#fff;border:1px solid #d5deea;border-radius:10px;padding:12px;overflow:hidden}.density .row{border-bottom:1px solid #e4e8f1;display:flex;align-items:center;justify-content:space-between;font-size:12px}.density .row span:last-child{font-size:10px;background:#e5f3ed;color:#22634d;padding:3px 6px;border-radius:4px}
.corner{width:83%;margin:4px auto;background:#fff;border:1px solid #cdd6e8;padding:20px;box-shadow:0 6px 18px #2537610c}.corner strong{display:block;font-size:20px;margin-bottom:10px}.corner p{font-size:13px;color:#526078}.corner .button{font-size:13px;padding:10px 14px}
.type{padding:10px 16px;background:#fff;border-radius:10px}.type small{color:#526078;font-family:Arial,sans-serif;font-size:12px;letter-spacing:2px}.type h3{font-size:32px;margin:13px 0}.type p{font-size:16px;line-height:1.5;margin:0 0 12px}.type span{font-size:14px}
.icons{display:flex;align-items:center;justify-content:space-evenly;height:100%;color:#4f57b8}.icons svg{width:56px;height:56px;overflow:visible}.icons figure{margin:0;text-align:center}.icons figcaption{font-size:12px;color:#526078;margin-top:12px}
.backdrop{display:grid;place-items:center;border-radius:12px;overflow:hidden;position:relative;background:#d9e6f5}.glass-card{z-index:2;background:#fffffff0;color:#1d2c42;padding:16px 22px;border-radius:12px;box-shadow:0 5px 20px #26324e20;max-width:80%;font-size:16px}.glass-card span{display:block;font-size:12px;color:#526078;margin-top:6px}
.bg-gradient{background:linear-gradient(120deg,#b6d8ef,#ddd2ef)}.bg-mesh{background:radial-gradient(at 10% 15%,#9fe0da,transparent 65%),radial-gradient(at 90% 20%,#f0bad4,transparent 70%),radial-gradient(at 45% 100%,#a8b9ed,transparent 65%),#f3e8f5}
.bg-svg-pattern{background-color:#e4eaf4;background-image:radial-gradient(#9baecb 1.5px,transparent 1.5px);background-size:18px 18px}
.bg-image,.bg-video{background:linear-gradient(180deg,#a3c9e3 0 48%,#799c8f 48% 65%,#3e6863 65%);isolation:isolate}.bg-image:before,.bg-video:before{content:'';position:absolute;inset:30% -10% -40%;background:#668e8a;transform:rotate(-13deg);z-index:-1}.bg-video .glass-card:after{content:'▶  Video placeholder';display:block;margin-top:10px;font-size:12px;color:#4e5d77}
.bg-animated{background:radial-gradient(ellipse at 20% 40%,#c3b4ee,transparent 60%),radial-gradient(ellipse at 85% 75%,#8bdbd3,transparent 60%),#e7e7f7}
.bg-particles{background-color:#152b46;background-image:radial-gradient(#96c2df 1px,transparent 2px),radial-gradient(#b5d9ef 2px,transparent 3px);background-size:31px 43px,67px 53px}
.bg-3d{background:repeating-conic-gradient(from 30deg,#b8c9e1 0 60deg,#dce6f5 60deg 120deg,#9eafd0 120deg 180deg);background-size:75px 130px}.bg-texture{background:repeating-linear-gradient(25deg,#e5e0d8 0 1px,#f1ede7 1px 4px)}
.story{display:flex;align-items:center;gap:12px;height:100%;padding:8px}.frame{position:relative;flex:1;height:110px;border:1px solid #d0d9e9;border-radius:12px;background:#fff;overflow:hidden}.frame small{position:absolute;bottom:8px;left:10px;color:#63718a;font-size:12px}.orb{position:absolute;top:20px;width:32px;height:32px;border-radius:10px;background:#6660c8}.arrow{color:#7d87a0;font-size:24px}.motion-label{font-size:14px;color:#526078;margin:0 10px}
.logo-preview{background:#fff;border:1px solid #d6deec;border-radius:10px;position:relative}.logo-preview .shell-top{height:43px;border-bottom:1px solid #d6deec;background:#f9faff}.logo-preview .shell-nav{position:absolute;left:0;top:43px;bottom:0;width:92px;border-right:1px solid #d6deec;background:#eef1f8;padding:16px 10px;font-size:11px;line-height:2.5;color:#607089}.logo-preview .logo{position:absolute;top:12px;display:flex;gap:5px;align-items:center;font-size:12px;font-weight:700}.logo-preview .mark{display:inline-grid;place-items:center;background:#5751bd;color:#fff;width:20px;height:20px;border-radius:6px;font-size:10px}.logo-preview .placeholder{position:absolute;top:67px;left:115px;right:20px;height:80px;background:linear-gradient(#e9edf8 0 25%,transparent 25% 43%,#f1f4fa 43%);border-radius:8px}
@media(max-width:700px){main{width:100%;padding:20px}.grid,.grid.three{grid-template-columns:1fr}}
"""


def mini(style="minimal", extra="", root=ROOT):
    recipe = read_json(root, "design-library/catalog.json")[style]
    tokens = f"--radius:{recipe['radius']}px;--shadow:{recipe['shadow']};font-family:{recipe['font']}"
    aside = '<aside>Details<br>Owner<br>Notes</aside>' if extra == "nav-dual" else ""
    return f'''<div class="mini style-{style} {extra}" style="{tokens}">
    <nav><div class="brand">FORMA</div><span class="active">Overview</span><span>Projects</span><span>Team</span><span>Settings</span></nav>
    <section><div class="top"><strong>Workspace</strong><span class="button">+ New project</span></div>
    <div class="stats"><div class="stat"><small>Active projects</small><b>24</b></div><div class="stat"><small>Completed</small><b>18</b></div></div>
    <div class="activity"><div class="line"><span>Website refresh</span><span>72%</span></div><div class="bar"><i></i></div></div></section>{aside}</div>'''


def icon_preview(value):
    paths = ['<path d="M5 21 24 5l19 16v22H29V29H19v14H5Z"/>',
             '<path d="M4 12h16l5 6h19v24H4Z"/>',
             '<path d="M6 42V25h8v17Zm14 0V15h8v27Zm14 0V5h8v37Z"/>']
    attrs = {'outline': 'fill="none" stroke="currentColor" stroke-width="2"',
             'filled': 'fill="currentColor"',
             'duotone': 'fill="currentColor" fill-opacity=".22" stroke="currentColor" stroke-width="2"',
             'rounded': 'fill="none" stroke="currentColor" stroke-width="3.8" stroke-linejoin="round" stroke-linecap="round"'}[value]
    return '<div class="icons">' + ''.join(f'<figure><svg viewBox="0 0 48 48" aria-hidden="true" {attrs}>{path}</svg><figcaption>{label}</figcaption></figure>' for path, label in zip(paths, ("Home", "Projects", "Reports"))) + '</div>'


def preview(question, choice, root=ROOT):
    path, value = question["path"], choice["value"]
    if path == "design.style":
        return mini(value, root=root), read_json(root, "design-library/catalog.json")[value]["description"]
    if path == "design.theme":
        if value == "system":
            return '<div class="system-pair">' + mini(root=root) + mini(extra="theme-dark", root=root) + '</div>', "Switches between light and dark with the device."
        return mini(extra="theme-dark" if value == "dark" else "", root=root), "Same content, different surface and text colors."
    if path == "design.palette":
        colors = read_json(root, "design-engine/palettes/catalog.json")[value]
        swatches = ''.join(f'<span style="background:{color}"></span>' for color in colors)
        hexes = ''.join(f'<span>{color}</span>' for color in colors)
        return f'<div><div class="swatches">{swatches}</div><div class="hexes">{hexes}</div><div class="palette-ui" style="background:{colors[0]};color:{colors[-1]}">Workspace <span style="background:{colors[2]};width:50px;height:10px;border-radius:5px"></span></div></div>', "Exact catalog swatches; final UI needs semantic contrast checks."
    if path == "design.navigation.type":
        key = {"left-sidebar":"", "right-sidebar":"nav-right", "top-navigation":"nav-top", "bottom-navigation":"nav-bottom", "floating-sidebar":"nav-floating", "dual-sidebar":"nav-dual", "centered":"nav-centered", "bento-dashboard":"nav-bento"}[value]
        return mini(extra=key, root=root), "Navigation placement concept; responsive behavior is designed later."
    if path == "design.density":
        height, count = {"compact":(24,7), "comfortable":(36,5), "spacious":(53,3)}[value]
        rows = ''.join(f'<div class="row" style="height:{height}px"><span>Project {i + 1:02d}</span><span>In progress</span></div>' for i in range(count))
        return f'<div class="density">{rows}</div>', "Same panel height: compare row spacing and visible content."
    if path == "design.borderRadius":
        return f'<div><div class="corner" style="border-radius:{value}px"><strong>Project details</strong><p>A card, an input and an action.</p><div style="border:1px solid #cdd6e8;padding:8px;margin-bottom:10px;border-radius:{value}px;font-size:12px">Project name</div><span class="button" style="--accent:#5b55bc;--radius:{value}px">Save project</span></div></div>', f"All three surfaces use a {value}px corner radius at this preview scale."
    if path == "design.typography":
        font, weight, tracking = {"modern":("Arial, sans-serif",700,0), "corporate":("Tahoma, sans-serif",700,0), "technical":("Consolas, monospace",700,0), "luxury":("Georgia, serif",400,.5), "minimalist":("Arial, sans-serif",400,-.6)}[value]
        return f'<div class="type" style="font-family:{font}"><small>PROJECT WORKSPACE</small><h3 style="font-weight:{weight};letter-spacing:{tracking}px">Make room for ideas.</h3><p>Plan the next chapter.<br>Keep every detail in view.</p><span>Aa Bb Cc &nbsp; 0123456789</span></div>', "Illustrative type direction; system font availability may vary."
    if path == "design.icons":
        return icon_preview(value), "Same three symbols in each treatment; keep labels for accessibility."
    if path == "design.background.type":
        notes = {"image":"Illustrated image placeholder; supply a real licensed image later.", "video":"Static video placeholder, not playable footage.", "animated":"Still frame of an animated-background concept.", "particles":"Still frame of a particle-background concept.", "3d":"Flat illustration of a 3D-background concept, not a 3D scene."}
        return f'<div class="backdrop bg-{value}"><div class="glass-card"><b>Space to create</b><span>Readable content comes first.</span></div></div>', notes.get(value, "Static background concept behind the same content card.")
    if path == "design.motion":
        positions, description = {"minimal":([12,16,18], "Small change · quick feedback"), "smooth":([12,43,75], "Even travel · gentle ease"), "cinematic":([12,30,75], "Longer entrance · staged reveal"), "spring":([12,85,75], "Overshoot · settle"), "disabled":([75,75,75], "No movement · immediate state")}[value]
        frames = []
        for i, position in enumerate(positions):
            opacity = [.25,.65,1][i] if value == "cinematic" else 1
            frames.append(f'<div class="frame"><span class="orb" style="left:{position}%;opacity:{opacity}"></span><small>{("Start", "Middle", "End")[i]}</small></div>')
        return '<div class="story">' + '<span class="arrow">→</span>'.join(frames) + '</div>', "Static storyboard, not an animation. " + description + ". Honor reduced motion."
    if path == "design.logoPosition":
        pos = {"top-left":"left:12px", "top-center":"left:50%;transform:translateX(-50%)", "top-right":"right:12px", "sidebar":"left:10px;top:60px"}[value]
        return f'<div class="logo-preview"><div class="shell-top"></div><div class="shell-nav" style="padding-top:{45 if value == "sidebar" else 16}px">Overview<br>Projects<br>Team</div><div class="logo" style="{pos}"><span class="mark">F</span> Forma</div><div class="placeholder"></div></div>', "Example mark and app name; use your own branding in the final design."
    raise ValueError("No visual sample implementation for " + path)


def build_sample_documents(root=ROOT):
    """Return one complete self-contained HTML sheet per question/expanded menu."""
    documents = {}
    for stage in load_uiux_flow(root)["steps"]:
        for question in stage["questions"]:
            for expanded in ([False, True] if question.get("primary") else [False]):
                cards, options = [], []
                for i, choice in enumerate(question_choices(question, root, expanded)):
                    code = str(i + 1) if expanded else chr(65 + i)
                    art, note = preview(question, choice, root)
                    label = escape(choice["label"])
                    cards.append(f'<article class="option"><div class="caption"><span class="code">{code}</span><h2>{label}</h2></div><div class="preview">{art}</div><div class="detail">{escape(note)}</div></article>')
                    options.append({"code":code, "value":choice["value"], "label":choice["label"]})
                columns = "three" if question["path"] in ("design.theme", "design.density") else "one" if question["path"] == "design.motion" else ""
                title = f"All {len(options)} style directions" if expanded else question["label"]
                html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><style>{CSS}</style></head>
<body><main><header><div class="eyebrow">APPFORGE / DESIGN CHOICES</div><h1>{escape(title)}</h1><p>Compare the labeled samples. Reply with a matching option, Auto, or Custom.</p></header>
<div class="grid {columns}">{''.join(cards)}</div><footer>Illustrative concepts · not a finished application · sample content only</footer></main></body></html>
'''
                filename = sample_path(question, expanded).removesuffix(".png") + ".html"
                documents[filename] = {"html":html, "path":question["path"], "expanded":expanded, "options":options}
    return documents


def sample_digest(documents):
    contents = {path: entry["html"] for path, entry in documents.items()}
    return hashlib.sha256(json.dumps(contents, sort_keys=True).encode()).hexdigest()


def check_samples(root=ROOT):
    """Validate sources, option mapping and committed PNGs without a browser."""
    root = Path(root)
    documents = build_sample_documents(root)
    manifest = read_json(root, "assets/uiux/manifest.json")
    if manifest.get("schemaVersion") != 1 or manifest.get("sourceDigest") != sample_digest(documents):
        raise ValueError("Visual samples are stale. Run python scripts/build_uiux_samples.py --render")
    expected = {path.removesuffix(".html") + ".png" for path in documents}
    if set(manifest["samples"]) != expected:
        raise ValueError("Visual sample manifest is incomplete")
    for relative, entry in documents.items():
        if (root / relative).read_text(encoding="utf-8") != entry["html"]:
            raise ValueError("Stale visual sample source: " + relative)
        png_path = relative.removesuffix(".html") + ".png"
        record = manifest["samples"][png_path]
        raw = (root / png_path).read_bytes()
        if (raw[:8] != b"\x89PNG\r\n\x1a\n" or len(raw) < 33
                or hashlib.sha256(raw).hexdigest() != record["sha256"]):
            raise ValueError("Missing or changed visual sample: " + png_path)
        dimensions = list(struct.unpack(">II", raw[16:24]))
        if dimensions != record["dimensions"] or dimensions[0] != 1200 or dimensions[1] < 300:
            raise ValueError("Invalid visual sample dimensions: " + png_path)
        if record["options"] != entry["options"] or record["path"] != entry["path"] or record["expanded"] != entry["expanded"]:
            raise ValueError("Visual sample labels do not match the menu: " + png_path)
    return len(documents)
