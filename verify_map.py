import asyncio, json
from playwright.async_api import async_playwright
BASE="http://127.0.0.1:8000"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width":1440,"height":950})
        pg = await ctx.new_page(); sends=[]
        pg.on("request", lambda r: sends.append(json.loads(r.post_data)) if "/answer" in r.url and r.post_data else None)
        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.fill("#email","student@aidachilembwe.ac.mw"); await pg.fill("#password","Student@Aida2026")
        await pg.click("button[type=submit]"); await pg.wait_for_url("**/dashboard")
        for trial in range(3):
            await pg.goto(f"{BASE}/quiz", wait_until="networkidle")
            await pg.click("button:has-text('Start quiz')")
            await pg.wait_for_selector(".question-card"); await pg.wait_for_timeout(500)
            # pick the 2nd displayed option for a single-choice question
            opts = pg.locator(".question-card .option")
            kind = await pg.locator(".question-card .option__letter").first.inner_text()
            if kind in ("A","B","C","D"):
                await opts.nth(1).click(); await pg.wait_for_timeout(800)
                sent = sends[-1]["given"]
                correct_display = await pg.locator(".question-card .option.correct").count()
                # find which displayed index carries the .correct class
                idx = None
                n = await opts.count()
                for i in range(n):
                    cls = await opts.nth(i).get_attribute("class")
                    if "correct" in cls: idx = i
                fb = (await pg.locator(".feedback h4").inner_text()).strip()
                print(f"trial {trial}: sent={sent} correct-displayed-index={idx} feedback={fb}")
                assert (idx == 1) == ("Correct" in fb), "MISMATCH between visual and grading"
            # abandon
            await pg.evaluate("history.back()")
        print("✓ shuffle mapping verified: displayed marking always matches server grading")
        await b.close()
asyncio.run(main())
