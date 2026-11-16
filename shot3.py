import asyncio, os
from playwright.async_api import async_playwright
BASE="http://127.0.0.1:8000"; OUT="/home/user/shots"
async def main():
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

        await pg.goto(f"{BASE}/quiz", wait_until="networkidle")
        await pg.click("button:has-text('Start quiz')")
        await pg.wait_for_selector(".question-card", timeout=15000)
        await pg.wait_for_timeout(600)
        correct_hits = 0
        answered = 0
        for i in range(10):
            # answer according to question type
            opts = pg.locator(".question-card .option")
            if await opts.count():
                await opts.nth(0).click()
            inp = pg.locator(".question-card input.input, .question-card textarea")
            if await inp.count():
                await inp.first.fill("bandwidth is capacity")
                await pg.locator(".question-card button:has-text('Save answer')").click()
            sel = pg.locator(".question-card select").first
            if await sel.count():
                o = await sel.locator("option").all()
                if len(o) > 1: await sel.select_option(index=1)
            await pg.wait_for_timeout(700)
            answered += 1
            if i == 0:
                # validate the visual mark matches the reported answer
                marked = await pg.locator(".question-card .option.correct").count()
                fb = await pg.locator(".feedback h4").inner_text()
                print(f"first question: marked-correct options={marked}, feedback='{fb.strip()}'")
                await pg.screenshot(path=f"{OUT}/12-quiz-feedback.png", full_page=True)
            nxt = pg.locator(".quiz-footer button:has-text('Next')")
            if await nxt.count():
                await nxt.click(); await pg.wait_for_timeout(250)
        print("questions answered:", answered)
        await pg.click("button:has-text('Submit quiz')"); await pg.wait_for_timeout(400)
        await pg.click(".modal button:has-text('Submit and mark')")
        await pg.wait_for_url("**/results/**", timeout=20000); await pg.wait_for_timeout(1200)
        await pg.screenshot(path=f"{OUT}/14-result.png", full_page=True)
        print("result:", pg.url)
        # verify review section shows answer tags
        tags = await pg.locator(".option .pill").count()
        print("review answer tags rendered:", tags)

        await pg.goto(f"{BASE}/dashboard", wait_until="networkidle"); await pg.wait_for_timeout(900)
        await pg.screenshot(path=f"{OUT}/02-dashboard.png", full_page=True)
        await pg.click("button[aria-label*='dark']"); await pg.wait_for_timeout(700)
        await pg.screenshot(path=f"{OUT}/15-dashboard-dark.png", full_page=True)
        await pg.goto(f"{BASE}/performance", wait_until="networkidle"); await pg.wait_for_timeout(1400)
        await pg.screenshot(path=f"{OUT}/16-performance.png", full_page=True)
        await pg.goto(f"{BASE}/terminology", wait_until="networkidle"); await pg.wait_for_timeout(900)
        await pg.screenshot(path=f"{OUT}/04-terms.png", full_page=False)
        await pg.click("button[aria-label*='light']"); await pg.wait_for_timeout(300)

        # admin
        await pg.evaluate("localStorage.clear()")
        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.fill("#email","admin@aidachilembwe.ac.mw"); await pg.fill("#password","Admin@Aida2026")
        await pg.click("button[type=submit]"); await pg.wait_for_url("**/admin", timeout=15000); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=f"{OUT}/17-admin.png", full_page=True)
        await pg.click("button[role=tab]:has-text('Questions')"); await pg.wait_for_timeout(900)
        await pg.screenshot(path=f"{OUT}/18-admin-questions.png", full_page=True)

        mob = await b.new_context(viewport={"width":390,"height":844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        mp = await mob.new_page()
        await mp.goto(f"{BASE}/login", wait_until="networkidle")
        await mp.fill("#email","student@aidachilembwe.ac.mw"); await mp.fill("#password","Student@Aida2026")
        await mp.click("button[type=submit]"); await mp.wait_for_url("**/dashboard"); await mp.wait_for_timeout(1200)
        await mp.screenshot(path=f"{OUT}/19-mobile-dashboard.png", full_page=True)
        await mp.goto(f"{BASE}/quiz", wait_until="networkidle")
        await mp.click("button:has-text('Start quiz')"); await mp.wait_for_selector(".question-card"); await mp.wait_for_timeout(600)
        await mp.screenshot(path=f"{OUT}/21-mobile-quiz.png", full_page=False)
        print("ERRORS:", errs[:8])
        await b.close()
asyncio.run(main())
