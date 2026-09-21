"""Record the 15s LinkedIn clickthrough: real usage, guaranteed tower inspect.

Writes a timestamped raw capture; trim the best 15s window with ffmpeg.
El guarantees: map zoom in -> tower inspector populated -> zoom out ->
ops inject/predict/rank -> topology node select.
"""
import time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
OUT = "/tmp/tourvid3"


def main():
    import pathlib
    pathlib.Path(OUT).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log = lambda m: print(f"{time.time()-t0:5.1f}s  {m}")
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 720},
                            record_video_dir=OUT, record_video_size={"width": 1280, "height": 720})
        pg = ctx.new_page()
        pg.goto(BASE + "#/", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        log("home")
        pg.get_by_role("link", name="Map", exact=True).click()
        pg.wait_for_selector("canvas", timeout=25000)
        pg.wait_for_function("!document.body.innerText.includes('loading…')", timeout=30000)
        pg.wait_for_timeout(1500)
        log("map loaded")
        box = pg.locator(".maplib-wrap canvas").bounding_box()
        cx, cy = box["x"] + box["width"] * 0.45, box["y"] + box["height"] * 0.5
        for _ in range(2):
            pg.mouse.dblclick(cx, cy)
            pg.wait_for_timeout(1200)
        # click until a tower inspector record appears (guaranteed money shot)
        import itertools
        hit = False
        for fx, fy in itertools.product([0.35, 0.45, 0.55, 0.65], [0.35, 0.45, 0.55, 0.65]):
            pg.mouse.click(box["x"] + box["width"] * fx, box["y"] + box["height"] * fy)
            pg.wait_for_timeout(350)
            if "MCC / MNC" in pg.locator(".inspect").inner_text():
                hit = True
                break
        log(f"tower inspect: {hit}")
        pg.wait_for_timeout(900)
        pg.mouse.move(cx, cy)
        for _ in range(3):
            pg.mouse.wheel(0, 400)
            pg.wait_for_timeout(350)
        log("zoomed out")
        pg.get_by_role("link", name="Ops AI", exact=True).click()
        pg.wait_for_timeout(900)
        pg.get_by_role("button", name="Inject satellite congestion").click()
        pg.wait_for_timeout(1600)
        log("injected")
        pg.keyboard.press("PageDown")
        pg.wait_for_timeout(500)
        pg.get_by_role("button", name="Predict degradation").click()
        pg.wait_for_timeout(1300)
        pg.get_by_role("button", name="Rank candidate satellites").click()
        pg.wait_for_timeout(1300)
        log("ranked")
        pg.get_by_role("link", name="Topology", exact=True).click()
        pg.wait_for_timeout(1100)
        pg.locator(".topo-group li button").first.click()
        pg.wait_for_timeout(900)
        log("topology done")
        pg.close()
        ctx.close()
        b.close()


if __name__ == "__main__":
    main()
