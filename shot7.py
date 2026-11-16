import asyncio
from playwright.async_api import async_playwright
BASE="http://127.0.0.1:8000"; OUT="/home/user/shots/final"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width":1440,"height":1000})
        pg = await ctx.new_page(); errs=[]
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.fill("#email","admin@aidachilembwe.ac.mw"); await pg.fill("#password","Admin@Aida2026")
        await pg.click("button[type=submit]"); await pg.wait_for_url("**/admin"); await pg.wait_for_timeout(1500)
        await pg.click("button[role=tab]:has-text('Questions')"); await pg.wait_for_timeout(900)
        await pg.click("button:has-text('New question')"); await pg.wait_for_timeout(800)
        await pg.set_viewport_size({"width":1440,"height":1500})
        await pg.screenshot(path=f"{OUT}/admin-new-question.png", full_page=True)
        # set an image on an existing question via API then confirm the student sees it
        print("ERRORS:", errs[:5])
        await b.close()
asyncio.run(main())
