"""Layout regression check: no page-level horizontal overflow on any route.

Asserts document.scrollWidth <= viewport width (desktop 1280 + mobile 390),
including the Ops page AFTER driving long AI-generated content into it
(incident rows with ISO timestamps, predictions, handoff, what-if, copilot).
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
ROUTES = ["#/", "#/map", "#/ops", "#/topology", "#/sources", "#/recruiter"]
VIEWPORTS = [(1280, 720), (390, 844)]


def overflow_px(pg) -> int:
    return pg.evaluate(
        "() => Math.max(0, document.documentElement.scrollWidth - window.innerWidth)")


def main():
    failures = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h in VIEWPORTS:
            pg = b.new_page(viewport={"width": w, "height": h})
            for route in ROUTES:
                pg.goto(BASE + route, wait_until="networkidle")
                pg.wait_for_timeout(2500 if route == "#/map" else 800)
                px = overflow_px(pg)
                print(f"{w}x{h} {route}: overflow={px}px")
                if px > 1:
                    failures.append((w, route, px))
            # Ops page with full AI content rendered
            pg.goto(BASE + "#/ops", wait_until="networkidle")
            pg.get_by_role("button", name="Inject satellite congestion").click()
            pg.wait_for_timeout(2000)
            pg.get_by_role("button", name="Predict degradation").click()
            pg.get_by_role("button", name="Rank candidate satellites").click()
            pg.get_by_role("button", name="Simulate SAT outage").click()
            pg.locator("input").fill("Why did you recommend this satellite?")
            pg.get_by_role("button", name="Ask").click()
            pg.wait_for_timeout(2500)
            px = overflow_px(pg)
            print(f"{w}x{h} #/ops (full AI content): overflow={px}px")
            if px > 1:
                failures.append((w, "#/ops-full", px))
            pg.close()
        b.close()
    if failures:
        print("FAIL:", failures)
        raise SystemExit(1)
    print("PASS: no horizontal overflow on any route/viewport")


if __name__ == "__main__":
    main()
