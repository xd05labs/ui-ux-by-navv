"""Semantic tokens with measured contrast, shared by previews and applications."""
import html
import json
from .catalog import catalogs


def rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, amount):
    return "#" + "".join(f"{round(x * (1 - amount) + y * amount):02x}" for x, y in zip(rgb(a), rgb(b)))


def luminance(color):
    values = [v / 255 for v in rgb(color)]
    values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(v * w for v, w in zip(values, (.2126, .7152, .0722)))


def contrast(a, b):
    light, dark = sorted([luminance(a), luminance(b)], reverse=True)
    return (light + .05) / (dark + .05)


def readable(color, background, minimum=4.5):
    target = max(["#000000", "#ffffff"], key=lambda c: contrast(c, background))
    for step in range(101):
        candidate = mix(color, target, step / 100)
        if contrast(candidate, background) >= minimum:
            return candidate
    return target


def tokens(config, mode):
    design = config["design"]
    palette = catalogs()["palettes"][design["palette"]]
    darkest = min(palette, key=luminance)
    lightest = max(palette, key=luminance)
    dark = mode == "dark"
    background = mix(darkest, "#000000", .3) if dark else mix(lightest, "#ffffff", .65)
    surface = mix(background, "#ffffff" if dark else "#000000", .055 if dark else .012)
    primary = readable(design["primaryColor"], surface)
    text = readable("#edf2fa" if dark else "#172437", surface)
    muted = readable("#9baabe" if dark else "#647085", surface)
    colors = {"background": background, "surface": surface,
              "surface-raised": mix(surface, "#ffffff" if dark else "#000000", .035),
              "primary": primary, "secondary": readable(palette[1], surface),
              "accent": readable(palette[3], surface), "text": text, "text-muted": muted,
              "on-primary": max(["#000000", "#ffffff"], key=lambda c: contrast(c, primary)),
              "border": mix(surface, text, .2), "control-border": readable("#77808e", surface, 3),
              "hover": mix(surface, primary, .08), "focus": readable(primary, surface, 3),
              "success": readable("#13845c", surface), "warning": readable("#a86306", surface),
              "error": readable("#ce3647", surface), "disabled": mix(surface, text, .5)}
    return colors


def contrast_report(config):
    result = {}
    for mode in ("light", "dark"):
        colors = tokens(config, mode)
        pairs = [(key, "surface", 4.5) for key in ("text", "text-muted", "primary", "success", "warning", "error")]
        pairs += [("on-primary", "primary", 4.5), ("focus", "surface", 3), ("control-border", "surface", 3)]
        result[mode] = [{"foreground": a, "background": b, "ratio": round(contrast(colors[a], colors[b]), 3),
                         "minimum": limit, "passed": contrast(colors[a], colors[b]) >= limit} for a, b, limit in pairs]
    return result


def css(config):
    design = config["design"]
    style = catalogs()["styles"][design["style"]]
    def variables(mode):
        return ";".join(f"--{key}:{value}" for key, value in tokens(config, mode).items()) + ";color-scheme:" + mode
    space = {"compact": ".75rem", "comfortable": "1.2rem", "spacious": "1.7rem"}[design["density"]]
    font = {"technical": "monospace", "luxury": "serif", "corporate": "Arial", "minimalist": "system-ui"}.get(design["typography"], style["font"])
    rules = f":root{{{variables('light')};--radius:{design['borderRadius']}px;--space:{space};--shadow:{style['shadow']};--font:{font}}}\n"
    if design["theme"] == "system":
        rules += "@media(prefers-color-scheme:dark){:root{" + variables("dark") + "}}\n"
    elif design["theme"] == "dark":
        rules += ":root{" + variables("dark") + "}\n"
    rules += '[data-theme="light"]{' + variables("light") + '}[data-theme="dark"]{' + variables("dark") + '}\n'
    if design["motion"] == "disabled":
        rules += "*{animation:none!important;transition:none!important;scroll-behavior:auto!important}\n"
    else:
        rules += "button,a,input,select{transition:background-color .16s,color .16s,border-color .16s}\n"
    background = design["background"]["type"]
    if background in ("gradient", "mesh"):
        rules += "body{background-image:radial-gradient(ellipse at 95% 0%,color-mix(in srgb,var(--primary) 8%,transparent),transparent 55%);background-attachment:fixed}\n"
    if background == "mesh":
        rules += "body{background-image:radial-gradient(at 20% 20%,color-mix(in srgb,var(--accent) 8%,transparent),transparent 55%),radial-gradient(at 90% 0%,color-mix(in srgb,var(--primary) 8%,transparent),transparent 60%)}\n"
    if background == "svg-pattern":
        rules += "body{background-image:radial-gradient(var(--border) 1px,transparent 1px);background-size:24px 24px}\n"
    return rules


def preview(config, blueprint):
    """Offline, escaped design concept; interactions never pretend to save data."""
    name = html.escape(config["project"]["name"])
    title = html.escape(blueprint["collection"])
    nav = "".join(f'<a href="#{key}">{label}</a>' for key, label in [("overview", "Overview"), ("records", title), ("design", "Design controls")])
    palette_options = "".join(f'<option value="{key}">{key.replace("-", " ").title()}</option>' for key in catalogs()["palettes"])
    style_options = "".join(f'<option value="{key}">{key.replace("-", " ").title()}</option>' for key in catalogs()["styles"])
    all_tokens = {key: {"light": tokens({**config, "design": {**config["design"], "palette": key, "primaryColor": value[2]}}, "light"),
                        "dark": tokens({**config, "design": {**config["design"], "palette": key, "primaryColor": value[2]}}, "dark")}
                  for key, value in catalogs()["palettes"].items()}
    all_tokens[config["design"]["palette"]] = {mode: tokens(config, mode) for mode in ("light", "dark")}
    script_data = json.dumps({"config": config, "tokens": all_tokens, "styles": catalogs()["styles"]}).replace("<", "\\u003c")
    from .catalog import ROOT
    base_css = (ROOT / "components" / "workspace.css").read_text(encoding="utf-8")
    return f'''<!doctype html><html lang="{config['project']['language']}" dir="{config['design']['direction']}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} — design concept</title><style>{css(config)}{base_css}</style></head>
<body data-layout="{config['design']['navigation']['type']}"><a class="skip" href="#main">Skip to content</a><aside class="sidebar"><a class="brand" href="#overview"><span class="brandmark">A</span>{name}</a><p class="eyebrow">WORKSPACE CONCEPT</p><nav aria-label="Preview navigation">{nav}</nav><div class="sidebar-foot">AppForge AI<br><small>Ask. Design. Generate.</small></div></aside>
<main id="main"><header class="topbar"><span>Workspace / Design preview</span><span class="pill">Preview · sample data</span></header><section id="overview"><p class="eyebrow">YOUR NEXT CHAPTER</p><div class="heading-row"><div><h1>A little clarity.<br>A lot of possibility.</h1><p class="muted">{html.escape(config['project']['objective'])}</p></div><a class="button" href="#design">Customize design <span aria-hidden="true">↗</span></a></div><div class="stats"><article class="card"><span class="muted">Total {title.lower()}</span><strong>128</strong><span class="trend">↑ 12.8% this month</span></article><article class="card"><span class="muted">In progress</span><strong>24</strong><span class="muted">Across your workspace</span></article><article class="card"><span class="muted">Completion rate</span><strong>94<span class="unit">%</span></strong><span class="trend">↑ 8.2% this month</span></article></div></section>
<section class="card" id="records"><div class="section-heading"><div><p class="eyebrow">THE BIG PICTURE</p><h2>Recent {title.lower()}</h2></div><span class="pill">Illustrative records</span></div><div class="table-wrap"><table><thead><tr><th>Name</th><th>Status</th><th>Updated</th></tr></thead><tbody><tr><td>Website refresh</td><td><span class="badge">{html.escape(blueprint['statuses'][0])}</span></td><td>Today</td></tr><tr><td>Brand exploration</td><td><span class="badge">{html.escape(blueprint['statuses'][-1])}</span></td><td>Yesterday</td></tr></tbody></table></div></section>
<section class="card" id="design"><p class="eyebrow">MAKE IT YOURS</p><h2>Design controls</h2><p class="muted">Explore tokens here. Copy the configuration and import it with <code>appforge import</code> to keep changes.</p><div class="form-grid"><label>Visual style<select id="style">{style_options}</select></label><label>Color palette<select id="palette">{palette_options}</select></label><label>Theme<select id="theme"><option>light</option><option>dark</option><option>system</option></select></label><label>Corner radius<input id="radius" type="range" min="0" max="32" value="{config['design']['borderRadius']}"></label></div><button id="copy" type="button">Copy configuration JSON</button><p id="copy-status" role="status"></p><label>Configuration JSON<textarea id="configuration" rows="6" readonly></textarea></label></section><footer>Design concept only. Review requirements.md and architecture.md before approval.</footer></main>
<script>const data={script_data};const config=data.config;const root=document.documentElement;const pick=id=>document.getElementById(id);for(const [id,key] of [['style','style'],['palette','palette'],['theme','theme']])pick(id).value=config.design[key];
function update(){{config.design.style=pick('style').value;config.design.palette=pick('palette').value;config.design.theme=pick('theme').value;config.design.borderRadius=Number(pick('radius').value);const mode=config.design.theme==='system'?(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'):config.design.theme;const colors=data.tokens[config.design.palette][mode];for(const [k,v] of Object.entries(colors))root.style.setProperty('--'+k,v);const style=data.styles[config.design.style];root.style.setProperty('--shadow',style.shadow);root.style.setProperty('--font',style.font);root.style.setProperty('--radius',config.design.borderRadius+'px');root.style.colorScheme=mode;pick('configuration').value=JSON.stringify(config,null,2);}}
for(const id of ['style','palette','theme','radius'])pick(id).addEventListener('input',update);pick('palette').addEventListener('input',()=>{{config.design.primaryColor={json.dumps(catalogs()['palettes'])}[pick('palette').value][2];update();}});pick('copy').onclick=async()=>{{try{{await navigator.clipboard.writeText(pick('configuration').value);pick('copy-status').textContent='Configuration copied.';}}catch(e){{pick('configuration').select();pick('copy-status').textContent='Select and copy the configuration below.';}}}};update();</script></body></html>'''
