import asyncio, sys
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8000"
OUT = "/home/user/shots"

async def main():
    import os; os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width":1440,"height":950}, device_scale_factor=1)
        pg = await ctx.new_page()
        errors = []
        pg.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type in ("error","warning") else None)
        pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.screenshot(path=f"{OUT}/01-login.png", full_page=False)
        await pg.fill("#email","student@aidachilembwe.ac.mw")
        await pg.fill("#password","Student@Aida2026")
        await pg.click("button[type=submit]")
        await pg.wait_for_url("**/dashboard", timeout=15000)
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=f"{OUT}/02-dashboard.png", full_page=True)
        print("dashboard ok")
        for path, name in [("/topics","03-topics"),("/terminology","04-terms"),("/quiz","05-quiz-setup"),
                           ("/exams","06-exams"),("/challenge","07-challenge"),("/performance","08-performance"),
                           ("/leaderboard","09-leaderboard"),("/profile","10-profile")]:
            await pg.goto(f"{BASE}{path}", wait_until="networkidle"); await pg.wait_for_timeout(900)
            await pg.screenshot(path=f"{OUT}/{name}.png", full_page=True)
            print(name, "ok")
        print("CONSOLE:", *errors[:15], sep="\n  ")
        await b.close()

asyncio.run(main())
