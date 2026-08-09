# -*- coding: utf-8 -*-
"""
10개 구단 선수풀(등록선수/육성선수) 참고자료 + need 보정
출처: 나무위키 <구단명>/선수단 (2026-08 기준)

⚠ 추출 완전성 편차
  - 등록선수 총원은 페이지·파싱 편차가 커서 팀 간 절대 비교에 부적합 → 참고용으로만 저장
  - 포수 등록 인원은 규모가 작아 누락 가능성이 낮음 → need 보정에 실제 사용
  - 육성선수 포지션 분포는 추출이 온전한 팀에 한해 보조 지표로 사용
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "data")

# (등록 P,C,IF,OF), (육성 P,C,IF,OF), 등록완전성, 육성완전성, 메모
R = {
 "키움": ((47,8,22,12), None, "high", "none",
          "투수 47명으로 리그 최다 수준. 정현우·박준현·김윤하 등 최근 상위픽 투수 축적 완료. 외야 12명으로 얇음"),
 "두산": ((45,9,16,12), None, "mid", "none",
          "포수 9명이나 양의지 이후 주전 승계 미정. 내야 16명 중 다수가 30대"),
 "KIA": (None, None, "low", "none",
          "페이지 파싱 불완전. 포수 3명(주효상·한준수·김태군) 확인 — 리그 최소 수준이며 김태군 노쇠"),
 "롯데": ((27,9,13,10), None, "mid", "none",
          "포수 9명이나 유강남 이후 손성빈·정보근 경쟁 미정착. 내야 13명으로 얇음"),
 "kt":  ((41,9,17,18), None, "high", "none",
          "외야 18명으로 최다. 포수는 장성우 의존도 높음"),
 "NC":  ((49,8,24,14), None, "high", "none",
          "명단 규모는 크나 마운드 실질 뎁스 저하. 김형준 외 포수 자원 부족"),
 "삼성": ((32,7,8,None), (23,4,None,None), "low", "mid",
          "육성 투수 23명 vs 육성 포수 4명 — 최근 드래프트 투수 편중이 팜 구성에 그대로 반영. 야수 파이프라인 빈약"),
 "SSG": ((26,5,14,16), (19,2,5,5), "high", "high",
          "등록 포수 5명·육성 포수 2명으로 안방 자원 최소. 최정·한유섬 등 코너 야수 노쇠화"),
 "한화": ((15,4,13,11), (20,2,3,8), "low", "high",
          "등록 포수 4명·육성 포수 2명 — 리그 최저 수준. 육성 내야 3명으로 내야 파이프라인도 고갈. "
          "반면 육성 투수 20명 + 문동주·황준서·김서현 등 1군 영건 선발 보유"),
 "LG":  ((13,4,8,7), (22,4,9,3), "low", "high",
          "등록 포수 4명(박동원 의존). 육성 외야 3명으로 외야 파이프라인 얇음"),
}

# 포수 니즈 보정: 등록 포수 인원 기준 (적을수록 +)
CATCH = {"키움":8,"두산":9,"KIA":3,"롯데":9,"kt":9,"NC":8,"삼성":7,"SSG":5,"한화":4,"LG":4}

rosters = {}
for tid,(reg,dev,rc,dc,memo) in R.items():
    rosters[tid] = {
        "registered": dict(zip(["P","C","IF","OF"], reg)) if reg else None,
        "development": dict(zip(["P","C","IF","OF"], dev)) if dev else None,
        "reg_completeness": rc, "dev_completeness": dc,
        "catchers_registered": CATCH[tid], "memo": memo,
        "source": "나무위키 <구단명>/선수단 (2026-08 기준)",
    }

# ── need 보정 ────────────────────────────────────────────────────
meta = json.load(open(os.path.join(OUT,"teams.json"), encoding="utf-8"))
POS = ["P","C","IF","OF"]
log = []
for t in meta["teams"]:
    tid = t["id"]; r = rosters[tid]
    before = dict(t["need"])
    # ① 포수: 등록 포수 4명 → +0.12, 9명 → -0.06 (선형)
    c = r["catchers_registered"]
    t["need"]["C"] = round(min(0.95, max(0.25, t["need"]["C"] + (6.5 - c) * 0.035)), 3)
    # ② 육성 파이프라인(추출 온전 팀만): 해당 포지션 육성 비중이 리그 기준 대비 낮으면 니즈 +
    if r["development"] and r["dev_completeness"] == "high":
        tot = sum(v for v in r["development"].values() if v)
        base = {"P":0.50,"C":0.10,"IF":0.22,"OF":0.18}
        for k in POS:
            v = r["development"].get(k)
            if v is None: continue
            gap = base[k] - v / tot
            t["need"][k] = round(min(0.95, max(0.25, t["need"][k] + gap * 0.55)), 3)
    t["weight"] = {p: round(0.4*t["tendency"][p] + 0.6*t["need"][p], 3) for p in POS}
    t["roster"] = r
    diffs = {k: round(t["need"][k]-before[k], 3) for k in POS if abs(t["need"][k]-before[k])>=0.01}
    if diffs: log.append((tid, diffs))

meta["roster_note"] = ("등록선수 총원은 위키 파싱 편차로 팀 간 절대 비교에 부적합. "
                       "need 보정에는 ①등록 포수 인원(누락 가능성 낮음) ②육성선수 포지션 분포(추출 온전 팀 한정)만 사용")
json.dump(meta, open(os.path.join(OUT,"teams.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(rosters, open(os.path.join(OUT,"rosters.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)

print("need 보정 결과:")
for tid, d in log: print(f"  {tid:3s} {d}")
print("\n최종 가중치:")
for t in sorted(meta["teams"], key=lambda x:x["pick_order"]):
    print(f"  {t['pick_order']:2d}. {t['id']:3s} {t['weight']}")
