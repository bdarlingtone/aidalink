import asyncio, json, urllib.request
from playwright.async_api import async_playwright
BASE="http://127.0.0.1:8000"

def post(path, body, token=None):
    r = urllib.request.Request(BASE+path, method="POST", data=json.dumps(body).encode())
    r.add_header("Content-Type","application/json")
    if token: r.add_header("Authorization", f"Bearer {token}")
    return json.loads(urllib.request.urlopen(r).read())

tok = post("/api/auth/login", {"email":"student@aidachilembwe.ac.mw","password":"Student@Aida2026"})["access_token"]
paper = post("/api/quiz/start", {"mode":"quiz","qtypes":["mcq"],"count":5,"instant_feedback":True,"randomise":True}, tok)
aid = paper["attempt_id"]
q0 = paper["questions"][0]
print("order_map:", q0["input"]["order_map"], "-> canonical index of displayed option B =", q0["input"]["order_map"].get("1"))

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(viewport={"width":1280,"height":900})
        pg = await ctx.new_page()
        await pg.goto(f"{BASE}/login", wait_until="networkidle")
        await pg.fill("#email","student@aidachilembwe.ac.mw"); await pg.fill("#password","Student@Aida2026")
        await pg.click("button[type=submit]"); await pg.wait_for_url("**/dashboard")
        await pg.goto(f"{BASE}/quiz/{aid}", wait_until="networkidle")
        await pg.wait_for_selector(".question-card")
        await pg.wait_for_timeout(400)
        opts = pg.locator(".question-card .option")
        await opts.nth(1).click()   # click displayed option B
        await pg.wait_for_timeout(900)
        correct_idx = None
        for i in range(await opts.count()):
            if "correct" in (await opts.nth(i).get_attribute("class") or ""): correct_idx = i
        fb = (await pg.locator(".feedback h4").inner_text()).strip()
        expected_correct_display = [k for k,v in q0["input"]["order_map"].items() if v == 1]
        # server graded canonical index 1; the displayed option holding canonical 1 is the one marked correct
        print(f"clicked displayed B | marked-correct displayed index={correct_idx} | feedback={fb}")
        print(f"displayed index that maps to canonical 1: {expected_correct_display}")
        assert str(correct_idx) in expected_correct_display, "visual marking does not match canonical answer"
        assert ("Correct" in fb) == (correct_idx == 1), "feedback text disagrees with visual marking"
        print("✓ PASS: displayed marking, stored answer and grading all agree under shuffling")
        await b.close()
asyncio.run(main())
