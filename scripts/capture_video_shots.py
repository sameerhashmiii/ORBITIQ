"""Capture REAL ORBITIQ UI screenshots for the demo video (no fakes).

Runs against the live frontend (vite :5173) + backend (:8000).
Drives the actual demo flow: inject congestion -> predict -> rank -> what-if -> copilot.
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
OUT = "video/shots"


def main():
    import pathlib
    pathlib.Path(OUT).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(BASE + "#/", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{OUT}/01_home.png")
        pg.goto(BASE + "#/map", wait_until="networkidle")
        pg.wait_for_selector("canvas", timeout=20000)
        pg.wait_for_timeout(5000)  # let real map tiles + markers render
        pg.screenshot(path=f"{OUT}/02_map.png")
        pg.goto(BASE + "#/ops", wait_until="networkidle")
        pg.wait_for_timeout(1000)
        pg.get_by_role("button", name="Inject satellite congestion").click()
        pg.wait_for_timeout(2500)
        pg.get_by_role("heading", name="Incident Timeline").scroll_into_view_if_needed()
        pg.wait_for_timeout(500)
        pg.screenshot(path=f"{OUT}/03_incident.png")
        pg.get_by_role("button", name="Predict degradation").click()
        pg.get_by_role("button", name="Detect anomalies").click()
        pg.wait_for_timeout(2500)
        pg.get_by_role("heading", name="AI Predictions").scroll_into_view_if_needed()
        pg.wait_for_timeout(500)
        pg.screenshot(path=f"{OUT}/04_prediction.png")
        pg.get_by_role("button", name="Rank candidate satellites").click()
        pg.wait_for_timeout(2000)
        pg.get_by_role("heading", name="Handoff Optimization").scroll_into_view_if_needed()
        pg.wait_for_timeout(500)
        pg.screenshot(path=f"{OUT}/05_handoff.png")
        pg.get_by_role("button", name="Simulate SAT outage").click()
        pg.wait_for_timeout(2000)
        pg.get_by_role("heading", name="What-If Simulation").scroll_into_view_if_needed()
        pg.wait_for_timeout(500)
        pg.screenshot(path=f"{OUT}/06_whatif.png")
        pg.locator("input").fill("Why did you recommend this satellite?")
        pg.get_by_role("button", name="Ask").click()
        pg.wait_for_timeout(2000)
        pg.get_by_role("heading", name="GenAI Copilot").scroll_into_view_if_needed()
        pg.wait_for_timeout(500)
        pg.screenshot(path=f"{OUT}/07_copilot.png")
        pg.goto(BASE + "#/topology", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{OUT}/08_topology.png")
        pg.goto(BASE + "#/sources", wait_until="networkidle")
        pg.wait_for_timeout(1000)
        pg.screenshot(path=f"{OUT}/09_sources.png")
        b.close()
    print("shots captured in", OUT)


if __name__ == "__main__":
    main()
