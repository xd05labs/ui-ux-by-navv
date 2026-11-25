"""Build/check repository visual samples; --render uses optional Playwright."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from appforge.uiux_samples import build_sample_documents, check_samples, sample_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--render", action="store_true", help="Write HTML, render PNGs and update the manifest")
    actions.add_argument("--check", action="store_true", help="Check all sources, labels and image hashes without writing")
    args = parser.parse_args()
    if args.check:
        print(f"{check_samples(ROOT)} visual sample sheets current")
        return
    from playwright.sync_api import sync_playwright
    documents = build_sample_documents(ROOT)
    manifest = {"schemaVersion":1, "sourceDigest":sample_digest(documents), "samples":{}}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width":1200, "height":900}, device_scale_factor=1, reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for relative, entry in documents.items():
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(entry["html"], encoding="utf-8", newline="\n")
            page.goto(target.as_uri())
            page.evaluate("document.fonts.ready")
            assert page.locator(".option").count() == len(entry["options"])
            assert page.locator("h2").all_text_contents() == [choice["label"] for choice in entry["options"]]
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), relative
            clipped = page.locator(".caption, .detail").evaluate_all("els => els.some(e => e.scrollWidth > e.clientWidth || e.scrollHeight > e.clientHeight)")
            assert not clipped, "Clipped labels: " + relative
            png = target.with_suffix(".png")
            page.locator("main").screenshot(path=str(png), animations="disabled")
            raw = png.read_bytes()
            manifest["samples"][png.relative_to(ROOT).as_posix()] = {
                "path":entry["path"], "expanded":entry["expanded"], "options":entry["options"],
                "sha256":hashlib.sha256(raw).hexdigest(), "dimensions":list(struct.unpack(">II", raw[16:24]))}
            print("Rendered " + png.relative_to(ROOT).as_posix())
        assert not errors, errors
        browser.close()
    (ROOT / "assets/uiux/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{check_samples(ROOT)} visual sample sheets checked")


if __name__ == "__main__":
    main()
