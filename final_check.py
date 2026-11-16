"""Full browser regression pass: pages, quiz run, dark mode, mobile, admin."""
import asyncio, json
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8000"
OUT = "/home/user/shots/final"
PAGES = ["/dashboard", "/topics", "/topics/computer-networking", "/terminology", "/quiz",
         "/exams", "/challenge", "/performance", "/leaderboard", "/saved", "/profile"]

async def main():
    import os; os.makedirs(OUT, exist_ok=True)
    report = {"pages": {}, "errors": []}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 950})
        pg = await ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        pg.on("console", lambda m: errs.append(f"console: {m.text}") if m.type == "error" else None)

        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.fill("#email", "student@aidachilembwe.ac.mw")
        await pg.fill("#password", "Student@Aida2026")
        await pg.click("button[type=submit]")
        await pg.wait_for_url("**/dashboard")

        for path in PAGES:
            before = len(errs)
            await pg.goto(BASE + path, wait_until="networkidle")
            await pg.wait_for_timeout(900)
            txt = (await pg.inner_text("main")) if await pg.query_selector("main") else await pg.inner_text("body")
            report["pages"][path] = {"chars": len(txt), "new_errors": len(errs) - before, "title": (txt or "")[:60].replace("\n", " ")}
            await pg.screenshot(path=f"{OUT}/{path.strip('/').replace('/', '-')}.png", full_page=True)

        # full quiz run end-to-end
        await pg.goto(f"{BASE}/quiz", wait_until="networkidle")
        await pg.wait_for_timeout(700)
        await pg.click("button:has-text('Start')")
        await pg.wait_for_url("**/quiz/*")
        await pg.wait_for_timeout(900)
        total = int(await pg.inner_text(".quiz-progress__count")) if await pg.query_selector(".quiz-progress__count") else 0
        answered = 0
        for i in range(40):
            opts = await pg.query_selector_all(".option")
            if opts:
                await opts[0].click()
                await pg.wait_for_timeout(180)
                fb = await pg.query_selector(".feedback, .answer-panel")
                if fb:
                    btn = await pg.query_selector("button:has-text('Next question')")
                    if btn and await btn.is_enabled():
                        await btn.click()
                        await pg.wait_for_timeout(400)
                        continue
                else:
                    await pg.wait_for_timeout(200)
            nxt = await pg.query_selector("button:has-text('Next question'), button:has-text('Next')")
            if nxt and await nxt.is_enabled():
                await nxt.click(); await pg.wait_for_timeout(350)
            else:
                break
        await pg.screenshot(path=f"{OUT}/quiz-last.png")
        submit = await pg.query_selector("button:has-text('Submit')")
        if submit:
            await pg.click("button:has-text('Submit')"); await pg.wait_for_timeout(500)
            confirm = await pg.query_selector(".modal button:has-text('Submit')")
            if confirm:
                await confirm.click()
        try:
            await pg.wait_for_url("**/results/*", timeout=15000)
            await pg.wait_for_timeout(1500)
            await pg.screenshot(path=f"{OUT}/result.png", full_page=True)
            report["quiz"] = {"status": "completed", "url": pg.url}
        except Exception as e:
            report["quiz"] = {"status": "FAILED", "url": pg.url, "err": str(e)[:200]}

        # dark mode
        await pg.goto(f"{BASE}/dashboard", wait_until="networkidle")
        await pg.evaluate("document.documentElement.dataset.theme='dark'")
        await pg.wait_for_timeout(700)
        await pg.screenshot(path=f"{OUT}/dark-dashboard.png", full_page=True)
        await pg.evaluate("document.documentElement.dataset.theme='light'")

        # mobile
        mobile = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mp = await mobile.new_page()
        mp.on("pageerror", lambda e: errs.append(f"mobile pageerror: {e}"))
        await mp.goto(f"{BASE}/login", wait_until="networkidle")
        await mp.fill("#email", "student@aidachilembwe.ac.mw")
        await mp.fill("#password", "Student@Aida2026")
        await mp.click("button[type=submit]")
        await mp.wait_for_url("**/dashboard")
        await mp.wait_for_timeout(900)
        await mp.screenshot(path=f"{OUT}/mobile-dashboard.png", full_page=True)
        for path, name in [("/quiz", "mobile-quiz"), ("/terminology", "mobile-terminology")]:
            await mp.goto(BASE + path, wait_until="networkidle")
            await mp.wait_for_timeout(800)
            await mp.screenshot(path=f"{OUT}/{name}.png", full_page=True)

        # admin
        actx = await b.new_context(viewport={"width": 1440, "height": 1000})
        ap = await actx.new_page()
        ap.on("pageerror", lambda e: errs.append(f"admin pageerror: {e}"))
        await ap.goto(f"{BASE}/login", wait_until="networkidle")
        await ap.fill("#email", "admin@aidachilembwe.ac.mw")
        await ap.fill("#password", "Admin@Aida2026")
        await ap.click("button[type=submit]")
        await ap.wait_for_url("**/admin")
        for tab in ["Overview & analytics", "Questions", "Terminology", "Topics", "Students", "Audit log", "Settings"]:
            await ap.click(f"button[role=tab]:has-text('{tab}')")
            await ap.wait_for_timeout(900)
            await ap.screenshot(path=f"{OUT}/admin-{tab.split()[0].lower()}.png", full_page=True)
        # settings tab round-trip through the UI
        await ap.click("button[role=tab]:has-text('Settings')")
        await ap.wait_for_timeout(700)
        await ap.fill("#set-pass_mark", "55")
        await ap.click("button:has-text('Save settings')")
        await ap.wait_for_timeout(1200)
        await ap.screenshot(path=f"{OUT}/admin-settings-saved.png", full_page=True)
        await ap.fill("#set-pass_mark", "50")
        await ap.click("button:has-text('Save settings')")
        await ap.wait_for_timeout(900)

        # non-admin blocked from /admin
        await pg.goto(f"{BASE}/admin", wait_until="networkidle")
        await pg.wait_for_timeout(700)
        report["student_admin_blocked"] = "/admin" not in pg.url

        report["errors"] = errs
        await b.close()
    print(json.dumps(report, indent=2)[:4000])

asyncio.run(main())
