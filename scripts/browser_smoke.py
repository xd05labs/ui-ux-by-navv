"""Optional real-browser acceptance smoke test; artifacts are retained for review."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from appforge.config import defaults
from appforge.generator import generate
from appforge.planning import approve, create_plan
from appforge.state import Workspace, atomic, now


def main():
    from playwright.sync_api import sync_playwright, expect
    output = ROOT / "artifacts" / ("browser-" + uuid4().hex[:8])
    workspace = Workspace(output)
    workspace.initialize(defaults(name="Clarity Workspace"))
    create_plan(workspace); approve(workspace); generate(workspace)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    environment = {**os.environ, "APP_ORIGIN": origin, "APP_SECURE_COOKIES": "false", "APP_ALLOW_REGISTRATION": "true"}
    log = (output / "server.log").open("w", encoding="utf-8")
    server = subprocess.Popen([sys.executable, "server.py", "--port", str(port)], cwd=output / "generated-app", env=environment, stdout=log, stderr=log)
    report = {"at": now(), "checks": [], "viewports": [], "screenshots": [], "browserErrors": [], "passed": False}
    def passed(name):
        report["checks"].append({"name": name, "passed": True})
    try:
        for _ in range(100):
            try:
                with urlopen(origin + "/api/health", timeout=1) as response:
                    if response.status == 200: break
            except OSError:
                if server.poll() is not None: raise RuntimeError("Server exited; inspect server.log")
                time.sleep(.1)
        else:
            raise RuntimeError("Server did not become healthy")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            page.on("pageerror", lambda error: report["browserErrors"].append(str(error)))
            page.goto(origin)
            page.get_by_role("button", name="Create an account", exact=True).click()
            page.get_by_label("Email address").fill("demo@example.test")
            page.get_by_label("Password", exact=True).fill("an isolated browser password")
            page.get_by_role("button", name="Create account", exact=True).click()
            expect(page.locator("#workspace")).to_be_visible()
            passed("Registration, session and dashboard")
            page.locator('nav[aria-label="Main navigation"]').get_by_role("link", name="Projects", exact=True).click()
            page.locator('#records > .heading-row .create-record').click()
            page.get_by_label("Name", exact=True).fill("Website refresh")
            page.get_by_label("Description", exact=True).fill("Make the next chapter feel effortless.")
            page.get_by_label("Project owner").fill("Design team")
            page.get_by_role("button", name="Save record", exact=True).click()
            expect(page.get_by_role("button", name="Edit Website refresh", exact=True)).to_be_visible()
            passed("Create record through frontend and API")
            page.get_by_role("button", name="Edit Website refresh", exact=True).click()
            page.get_by_label("Name", exact=True).fill("Website launch")
            page.get_by_label("Status", exact=True).select_option("in-progress")
            page.get_by_role("button", name="Save record", exact=True).click()
            expect(page.get_by_role("button", name="Edit Website launch", exact=True)).to_be_visible()
            passed("Edit and status validation")
            page.get_by_role("searchbox").fill("absent record")
            expect(page.locator("#empty")).to_be_visible()
            page.get_by_role("searchbox").fill("Website")
            expect(page.get_by_role("button", name="Edit Website launch", exact=True)).to_be_visible()
            page.get_by_role("searchbox").fill("")
            passed("Search and empty state")
            with page.expect_download() as download:
                page.get_by_role("button", name="Export CSV").click()
            download.value.save_as(output / "records.csv")
            assert "Website launch" in (output / "records.csv").read_text(encoding="utf-8")
            passed("CSV download content")
            for title, status in [("Brand exploration", "completed"), ("Customer research", "planned")]:
                page.locator('#records > .heading-row .create-record').click()
                page.get_by_label("Name", exact=True).fill(title)
                page.get_by_label("Status", exact=True).select_option(status)
                page.get_by_role("button", name="Save record", exact=True).click()
                expect(page.get_by_role("button", name=f"Edit {title}", exact=True)).to_be_visible()
            page.locator('nav[aria-label="Main navigation"]').get_by_role("link", name="Overview", exact=True).click()
            expect(page.locator("#total-count")).to_have_text("3")
            page.locator('#command-open').focus()
            page.keyboard.press("Control+k"); expect(page.locator("#commands")).to_be_visible()
            assert page.evaluate("Boolean(document.activeElement.closest('#commands'))")
            page.keyboard.press("Tab")
            assert page.evaluate("Boolean(document.activeElement.closest('#commands'))")
            page.keyboard.press("Escape")
            expect(page.locator("#commands")).not_to_be_visible()
            expect(page.locator('#command-open')).to_be_focused()
            passed("Command palette and keyboard focus")
            page.locator('#main').evaluate('(node) => node.blur()')
            page.locator('#toast').wait_for(state='hidden')
            for width, height, label in [(1440,1000,"desktop"),(768,1024,"tablet"),(390,844,"mobile")]:
                page.set_viewport_size({"width":width,"height":height})
                page.screenshot(path=str(output / f"{label}.png"), full_page=True)
                overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                assert not overflow, f"Horizontal overflow at {width}"
                report["viewports"].append({"width":width,"height":height,"horizontalOverflow":overflow})
                report["screenshots"].append(str(output / f"{label}.png"))
            passed("Desktop, tablet and mobile overflow checks")
            page.set_viewport_size({"width":1440,"height":1000})
            page.locator('nav[aria-label="Main navigation"]').get_by_role("link", name="Settings", exact=True).click()
            page.locator('#theme').select_option("dark")
            expect(page.locator("html")).to_have_attribute("data-theme", "dark")
            page.locator('nav[aria-label="Main navigation"]').get_by_role("link", name="Overview", exact=True).click()
            expect(page.locator('#overview')).to_be_visible()
            expect(page.locator('#settings')).not_to_be_visible()
            page.screenshot(path=str(output / "dark.png"), full_page=True)
            passed("Theme hot swapping")
            page.locator('nav[aria-label="Main navigation"]').get_by_role("link", name="Activity", exact=True).click()
            expect(page.locator("#activity-list")).to_contain_text("Website launch")
            passed("Audit history")
            page.locator('nav[aria-label="Main navigation"]').get_by_role("link", name="Projects", exact=True).click()
            page.get_by_role("button", name="Delete Website launch", exact=True).click()
            page.get_by_role("button", name="Delete record", exact=True).click()
            expect(page.get_by_role("button", name="Edit Website launch", exact=True)).to_have_count(0)
            passed("Delete confirmation and persistence")
            page.get_by_role("button", name="Sign out", exact=True).click()
            expect(page.locator("#auth")).to_be_visible()
            page.get_by_label("Email address").fill("demo@example.test")
            page.get_by_label("Password", exact=True).fill("an isolated browser password")
            page.get_by_role("button", name="Sign in", exact=True).click()
            expect(page.locator("#workspace")).to_be_visible()
            passed("Logout and login")
            page.goto((output / "design-preview.html").as_uri())
            page.locator('#palette').select_option("emerald")
            page.locator('#style').select_option("minimal")
            config = json.loads(page.locator("#configuration").input_value())
            assert config["design"]["palette"] == "emerald" and config["design"]["style"] == "minimal"
            passed("Offline design controls and configuration export")
            browser.close()
        assert not report["browserErrors"], report["browserErrors"]
        report["passed"] = True
    except Exception as error:
        report["error"] = str(error)
        try:
            report["pageState"] = {"url": page.url, "body": page.locator('body').inner_text()[:10000]}
            page.screenshot(path=str(output / "failure.png"), full_page=True)
        except Exception:
            pass
        raise
    finally:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired: server.kill(); server.wait()
        log.close(); atomic(output / "browser-report.json", report)
        print(json.dumps({"passed":report["passed"],"checks":len(report["checks"]),"report":str(output / "browser-report.json")},indent=2))


if __name__ == "__main__":
    main()
