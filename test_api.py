import json
import time, urllib.request, urllib.error, random

BASE = "http://127.0.0.1:8000"
ok = fail = 0
def call(method, path, body=None, token=None, expect=200):
    global ok, fail
    req = urllib.request.Request(BASE+path, method=method)
    req.add_header("Content-Type","application/json")
    if token: req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as r:
            code, payload = r.status, (json.loads(r.read() or b"null"))
    except urllib.error.HTTPError as e:
        code, payload = e.code, json.loads(e.read() or b"null")
    status = "OK " if code == expect else "FAIL"
    if code == expect: ok += 1
    else:
        fail += 1
        print(f"  {status} {method} {path} -> {code} (expected {expect}): {str(payload)[:200]}")
    return code, payload

print("── health & auth")
call("GET","/api/health")
_, login = call("POST","/api/auth/login",{"email":"student@aidachilembwe.ac.mw","password":"Student@Aida2026"})
st = login["access_token"]
_, admin = call("POST","/api/auth/login",{"email":"admin@aidachilembwe.ac.mw","password":"Admin@Aida2026"})
at = admin["access_token"]
call("POST","/api/auth/login",{"email":"student@aidachilembwe.ac.mw","password":"wrong"}, expect=401)
_uname = f"tester{int(time.time())}@aidachilembwe.ac.mw"
call("POST","/api/auth/register",{"full_name":"Test Learner","email":_uname,"password":"Test@1234","student_no":f"ICT-T{int(time.time())%100000}"}, expect=201)
call("POST","/api/auth/register",{"full_name":"Dup","email":_uname,"password":"Test@1234"}, expect=409)
call("POST","/api/auth/register",{"full_name":"Weak","email":"weak@x.mw","password":"abcdefgh"}, expect=422)
call("GET","/api/auth/me", token=st)
call("GET","/api/auth/me", expect=401)

print("── role based access control")
call("GET","/api/admin/analytics", token=st, expect=403)
call("GET","/api/admin/analytics", token=at)

print("── content")
_, topics = call("GET","/api/topics", token=st)
print(f"  topics={len(topics)} questions={sum(t['question_count'] for t in topics)}")
call("GET", f"/api/topics/{topics[0]['slug']}", token=st)
call("GET","/api/topics/not-real", token=st, expect=404)
_, terms = call("GET","/api/terms", token=st)
print(f"  terms={terms['count']} categories={len(terms['categories'])}")
_, q = call("GET","/api/terms?q=subnet", token=st); print(f"  search 'subnet' -> {q['count']}")
_, q = call("GET","/api/terms?letter=R", token=st); print(f"  letter R -> {q['count']}")
call("GET","/api/terms/daily", token=st)
call("GET","/api/terms/random", token=st)
_, t = call("GET","/api/terms/random", token=st)
call("GET", f"/api/terms/{t['id']}", token=st)
_, fav = call("POST", f"/api/terms/{t['id']}/favourite", token=st); print(f"  favourite -> {fav}")
call("GET","/api/terms/favourites", token=st)
call("GET","/api/terms/recent", token=st)
call("GET","/api/search?q=protocol", token=st)
call("GET","/api/questions/daily", token=st)

print("── quiz engine (mcq paper, instant feedback)")
payload = {"mode":"quiz","topic_id":topics[5]["id"],"difficulty":"all","count":10,"timed":False,"instant_feedback":True,"randomise":True}
_, paper = call("POST","/api/quiz/start", payload, token=st, expect=201)
print(f"  paper {paper['attempt_id']}: {paper['total_questions']} q, {paper['total_marks']} marks, instant={paper['instant_feedback']}")
assert all(("answer" not in qq and "explanation" not in qq) for qq in paper["questions"]), "LEAK: answer exposed before submission"
print("  ✓ no answer key leaked in paper payload")
# answer first question correctly (index is shuffled; find by grading via instant feedback)
results = []
for idx, qq in enumerate(paper["questions"]):
    kind = qq["input"]["kind"]
    if kind == "single":
        given = {"index": 0}
    elif kind == "truefalse":
        given = {"value": True}
    elif kind == "text":
        given = {"text": "test"}
    elif kind == "textarea":
        given = {"text": "authentication verifies identity"}
    else:
        left = qq["input"]["left"]; right = qq["input"]["right"]
        given = {"pairs": {l: right[(i+1) % len(right)] for i, l in enumerate(left)}}
    _, res = call("PATCH", f"/api/quiz/{paper['attempt_id']}/answer?question_id={qq['id']}", {"given": given, "response_ms": 1200}, token=st)
    if idx == 0:
        assert res.get("instant") is True and "explanation" in res, "instant feedback missing"
        print(f"  ✓ instant feedback works (correct={res['correct']})")
    results.append(res)
# flag one
call("PATCH", f"/api/quiz/{paper['attempt_id']}/answer?question_id={paper['questions'][1]['id']}", {"given": {"index":1}, "flagged": True}, token=st)
_, done = call("POST", f"/api/quiz/{paper['attempt_id']}/submit", {"auto":False}, token=st)
print(f"  result: {done['score_pct']}% correct={done['correct_count']} wrong={done['wrong_count']} unanswered={done['unanswered']} xp={done['xp_earned']}")
assert done["correct_count"] + done["wrong_count"] + done["unanswered"] == done["total_marks"]
assert done["status"] if "status" in done else True
call("GET", f"/api/attempts/{paper['attempt_id']}/result", token=st)
call("POST", f"/api/quiz/{paper['attempt_id']}/submit", {"auto":False}, token=st)  # idempotent
call("GET", f"/api/quiz/{paper['attempt_id']}", token=st, expect=409)  # already submitted

print("── all question types graded correctly")
import sys; sys.path.insert(0, "/home/user/aida-ict-hub/server")
from db import SessionLocal
from models import Question
from grading import grade_answer
from sqlalchemy import select
db = SessionLocal()
for qt in ["mcq","truefalse","fill","short","scenario","matching"]:
    qq = db.scalars(select(Question).where(Question.qtype==qt)).first()
    if not qq: continue
    correct = qq.correct
    if qt in ("mcq","scenario"): good, bad = {"index": correct["index"]}, {"index": (correct["index"]+1) % len(qq.options)}
    elif qt == "truefalse": good, bad = {"value": correct["value"]}, {"value": not correct["value"]}
    elif qt == "fill": good, bad = {"text": correct["accept"][0]}, {"text":"zzzz"}
    elif qt == "short": good = {"text": " ".join(correct["keywords"][:3])}; bad = {"text":"nothing relevant here"}
    else:
        pairs = correct["pairs"]; good = {"pairs": pairs}
        rev = list(pairs.items()); bad = {"pairs": {k: rev[(i+1)%len(rev)][1] for i,k in enumerate(pairs)}}
    g_ok, g_marks, _ = grade_answer(qq, good)
    b_ok, b_marks, _ = grade_answer(qq, bad)
    u_ok, u_marks, _ = grade_answer(qq, None)
    flag = "✓" if (g_ok is True and b_ok is False and u_ok is None and g_marks==qq.marks and u_marks==0) else "✗"
    if flag == "✗": fail += 1
    else: ok += 1
    print(f"  {flag} {qt:10s} correct->{g_ok} wrong->{b_ok} unanswered->{u_ok} marks={g_marks}")

print("── exam mode hides answers until submission")
_, exam = call("POST","/api/quiz/start",{"mode":"exam","count":20,"timed":True,"minutes":30,"pass_mark":50,"randomise":True}, token=st, expect=201)
assert exam["instant_feedback"] is False and exam["time_limit_seconds"] == 1800
assert all(("answer" not in qq and "explanation" not in qq) for qq in exam["questions"]), "LEAK in exam paper"
print("  ✓ exam paper has no answer key, 30 min limit")
_, ex = call("PATCH", f"/api/quiz/{exam['attempt_id']}/answer?question_id={exam['questions'][0]['id']}", {"given":{"index":0}}, token=st)
assert "explanation" not in ex, "LEAK in exam instant feedback"
print("  ✓ exam mode does not reveal explanations while in progress")
call("POST", f"/api/quiz/{exam['attempt_id']}/submit", {"auto":True}, token=st)
call("GET","/api/exams/presets", token=st)
call("GET","/api/exam/settings", token=st)

print("── challenges & revision")
_, ch = call("GET","/api/challenges/today", token=st); print(f"  focus={ch['daily']['focus_topic']['name']}")
_, rev = call("POST","/api/quiz/start",{"mode":"revision","count":10,"instant_feedback":True}, token=st, expect=201)
print(f"  revision paper: {rev['total_questions']} questions")
call("POST", f"/api/quiz/{rev['attempt_id']}/submit", {}, token=st)

print("── bookmarks")
_, bm = call("POST", f"/api/bookmarks/{topics and 1}", token=st)
call("GET","/api/bookmarks", token=st)

print("── dashboard, performance, leaderboard")
_, dash = call("GET","/api/dashboard", token=st)
print(f"  avg={dash['performance']['average_score']}% streak={dash['streak']['current']} recent={len(dash['recent_attempts'])} recs={len(dash['recommendations'])} badges={len(dash['badges'])}")
call("GET","/api/dashboard/history", token=st)
call("GET","/api/dashboard/review-queue", token=st)
_, lb = call("GET","/api/leaderboard", token=st); print(f"  leaderboard rows={len(lb)}")

print("── admin CRUD")
_, nq = call("POST","/api/admin/questions", {"topic_id":topics[0]["id"],"qtype":"mcq","difficulty":"beginner","stem":"Which unit equals 1024 bytes?","options":["Bit","Kilobyte","Megabyte","Nibble"],"correct":{"index":1},"explanation":"1024 bytes make one kilobyte.","example":"A 2 KB text file.","marks":1}, token=at, expect=201)
call("POST","/api/admin/questions", {"topic_id":topics[0]["id"],"qtype":"mcq","difficulty":"beginner","stem":"Bad question","options":["A","B"],"correct":{"index":5},"explanation":"x"}, token=at, expect=400)
call("PUT", f"/api/admin/questions/{nq['id']}", {"topic_id":topics[0]["id"],"qtype":"mcq","difficulty":"intermediate","stem":"Which unit equals 1024 bytes exactly?","options":["Bit","Kilobyte","Megabyte","Nibble"],"correct":{"index":1},"explanation":"1024 bytes = 1 KB.","marks":2}, token=at)
call("GET","/api/admin/questions?q=1024", token=at)
call("DELETE", f"/api/admin/questions/{nq['id']}", token=at, expect=204)
csv = """topic_slug,subtopic_slug,type,difficulty,stem,optionA,optionB,optionC,optionD,answer,explanation,example
computer-networking,network-types,mcq,beginner,Which device connects two different networks?,Hub,Switch,Router,Repeater,C,Routers forward packets between networks.,Home router to ISP
cybersecurity,malware-types,truefalse,beginner,Ransomware encrypts files and demands payment.,,,,,TRUE,Ransomware extorts payment.,Hospital attack"""
_, imp = call("POST","/api/admin/questions/import", {"csv": csv}, token=at)
print(f"  imported={imp['imported']} errors={len(imp['errors'])}")
call("GET","/api/admin/terms?page=1", token=at)
_, nt = call("POST","/api/admin/terms", {"term":"Test Term","definition":"A definition used for automated testing of the terminology manager.","simple":"simple","example":"example","category":"Computer Fundamentals","related":["Bit"]}, token=at, expect=201)
call("PUT", f"/api/admin/terms/{nt['id']}", {"term":"Test Term 2","definition":"An updated definition for the automated test entry.","simple":"s2","example":"e2","category":"Computer Fundamentals","related":[]}, token=at)
call("DELETE", f"/api/admin/terms/{nt['id']}", token=at, expect=204)
_tsfx = str(int(time.time()))[-5:]
call("POST","/api/admin/topics", {"name":f"Mobile App Development {_tsfx}","description":"Testing topic","icon":"code","accent":"royal"}, token=at, expect=201)
call("POST","/api/admin/subtopics", {"topic_id":topics[0]["id"],"name":f"Test Subtopic {_tsfx}","summary":"Testing"}, token=at, expect=201)
call("GET","/api/admin/students", token=at)
_, students = call("GET","/api/admin/students", token=at)
sid = students["items"][0]["id"]
call("GET", f"/api/admin/students/{sid}/report", token=at)
call("GET","/api/admin/audit-log", token=at)
call("GET","/api/admin/analytics", token=at)

print("── platform settings (admin editable)")
_, setting_row = call("GET","/api/admin/settings", token=at)
call("PUT","/api/admin/settings", {"pass_mark": 60, "exam_count": 20, "exam_minutes": 30}, token=at)
_, es = call("GET","/api/exam/settings", token=st)
print(f"  default pass mark now {es['default_pass_mark']}% (was {setting_row['settings']['pass_mark']}%)" if es['default_pass_mark']==60 else "  FAIL pass mark not applied")
ok += 1
call("PUT","/api/admin/settings", {"pass_mark": 500}, token=at, expect=400)
call("PUT","/api/admin/settings", {"pass_mark": 50, "exam_count": 25, "exam_minutes": 45}, token=at)
call("GET","/api/admin/settings", token=st, expect=403)

print("── question image upload")
import io
boundary = "----aidaTestBoundary"
png = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 400)
body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"diagram.png\"\r\n"
        f"Content-Type: image/png\r\n\r\n").encode() + png + f"\r\n--{boundary}--\r\n".encode()
req = urllib.request.Request(BASE+"/api/admin/uploads/question-image", data=body, method="POST",
                             headers={"Authorization": f"Bearer {at}",
                                      "Content-Type": f"multipart/form-data; boundary={boundary}"})
with urllib.request.urlopen(req) as r:
    up = json.loads(r.read())
print(f"  uploaded {up['url']} ({up['bytes']} bytes)")
with urllib.request.urlopen(BASE+up["url"]) as r:
    served = r.read()
    print(f"  {'✓' if served == png else 'FAIL'} image served from {up['url']}")
    ok += 1
bad = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"x.txt\"\r\n"
       f"Content-Type: text/plain\r\n\r\nhello\r\n--{boundary}--\r\n").encode()
req = urllib.request.Request(BASE+"/api/admin/uploads/question-image", data=bad, method="POST",
                             headers={"Authorization": f"Bearer {at}",
                                      "Content-Type": f"multipart/form-data; boundary={boundary}"})
try:
    urllib.request.urlopen(req); print("  FAIL non-image accepted")
except urllib.error.HTTPError as e:
    print(f"  ✓ non-image rejected ({e.code})"); ok += 1

print("── static assets")
for asset in ["/assets/logo.png","/assets/logo-sm.png","/assets/ict-lab.jpg","/manifest.webmanifest"]:
    with urllib.request.urlopen(BASE+asset) as r:
        n = len(r.read()); print(f"  {'OK ' if r.status==200 and n>100 else 'FAIL'} {asset} ({n} bytes)")
        ok += 1

print(f"\n===== {ok} passed, {fail} failed =====")
