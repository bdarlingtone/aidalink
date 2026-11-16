import asyncio, os
from playwright.async_api import async_playwright
BASE="http://127.0.0.1:8000"; OUT="/home/user/shots"
async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width":1440,"height":950})
        pg = await ctx.new_page()
        errs=[]
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.fill("#email","student@aidachilembwe.ac.mw"); await pg.fill("#password","Student@Aida2026")
        await pg.click("button[type=submit]"); await pg.wait_for_url("**/dashboard")

        # run a quiz
        await pg.goto(f"{BASE}/quiz", wait_until="networkidle")
        await pg.click("text=Start quiz")
        await pg.wait_for_selector(".question-card", timeout=15000)
        await pg.wait_for_timeout(700)
        await pg.screenshot(path=f"{OUT}/11-quiz-run.png", full_page=True)
        # answer the first question (click first option) to see instant feedback
        opt = pg.locator(".option").first
        if await opt.count():
            await opt.click(); await pg.wait_for_timeout(900)
            await pg.screenshot(path=f"{OUT}/12-quiz-feedback.png", full_page=True)
        # go through remaining questions answering anything
        for i in range(12):
            nxt = pg.locator("button:has-text('Next')")
            if await nxt.count() == 0: break
            # choose an answer present on this question
            o = pg.locator(".option").first
            if await o.count(): await o.click()
            txt = pg.locator(".question-card input.input, .question-card textarea")
            if await txt.count(): await txt.first.fill("test answer")
            m = pg.locator(".question-card select").first
            if await m.count():
                opts = await m.locator("option").all()
                if len(opts)>1: await m.select_option(index=1)
            await nxt.first.click(); await pg.wait_for_timeout(250)
        await pg.screenshot(path=f"{OUT}/13-quiz-last.png", full_page=False)
        # submit
        await pg.click("button:has-text('Submit quiz')")
        await pg.wait_for_timeout(500)
        await pg.click(".modal button:has-text('Submit and mark')")
        await pg.wait_for_url("**/results/**", timeout=20000)
        await pg.wait_for_timeout(1200)
        await pg.screenshot(path=f"{OUT}/14-result.png", full_page=True)
        print("result url", pg.url)

        # dark mode dashboard
        await pg.goto(f"{BASE}/dashboard", wait_until="networkidle")
        await pg.click("button[aria-label*='dark']"); await pg.wait_for_timeout(800)
        await pg.screenshot(path=f"{OUT}/15-dashboard-dark.png", full_page=True)
        await pg.goto(f"{BASE}/performance", wait_until="networkidle"); await pg.wait_for_timeout(1200)
        await pg.screenshot(path=f"{OUT}/16-performance-dark.png", full_page=True)
        await pg.click("button[aria-label*='light']"); await pg.wait_for_timeout(600)

        # admin
        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.evaluate("localStorage.clear()")
        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.fill("#email","admin@aidachilembwe.ac.mw"); await pg.fill("#password","Admin@Aida2026")
        await pg.click("button[type=submit]"); await pg.wait_for_url("**/admin", timeout=15000)
        await pg.wait_for_timeout(1400)
        await pg.screenshot(path=f"{OUT}/17-admin.png", full_page=True)
        await pg.click("button[role=tab]:has-text('Questions')"); await pg.wait_for_timeout(1000)
        await pg.screenshot(path=f"{OUT}/18-admin-questions.png", full_page=True)

        # mobile
        mob = await b.new_context(viewport={"width":390,"height":844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        mp = await mob.new_page()
        await mp.goto(f"{BASE}/login", wait_until="networkidle")
        await mp.fill("#email","student@aidachilembwe.ac.mw"); await mp.fill("#password","Student@Aida2026")
        await mp.click("button[type=submit]"); await mp.wait_for_url("**/dashboard"); await mp.wait_for_timeout(1200)
        await mp.screenshot(path=f"{OUT}/19-mobile-dashboard.png", full_page=True)
        await mp.goto(f"{BASE}/terminology", wait_until="networkidle"); await mp.wait_for_timeout(900)
        await mp.screenshot(path=f"{OUT}/20-mobile-terms.png", full_page=False)
        print("ERRORS:", errs[:10])
        await b.close()
asyncio.run(main())
