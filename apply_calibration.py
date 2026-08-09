# -*- coding: utf-8 -*-
"""
②③④ 보정 일괄 적용

② 학년 재확인 (KBSA 고교부 전수 재조회, 2026-08-09)
   1차 스크래핑 정규식이 신장/체중/투타 미기재 선수를 통째로 건너뛰어 3학년을 1,113명으로 과소집계했다.
   학년만 읽는 관대한 패턴으로 재조회한 결과 3학년은 **1,230명**. 기존 '미등재 30명' 중 23명이
   실제로는 등재되어 있었고, 7명만 진짜 대상 외였다.

③ 포수 need 계수 축소 + 투수 비중 상향
   fm 110픽 대조: 포수 12.7% vs 5.6%(2.3배 과다), 투수 45.5% vs 58.9%(13%p 부족)

④ KBSA 신체 기반 talent 사전확률 — 나무위키 나열 순서 선형 감쇠 대체
   미평가(conf=low, perf 없음) 선수에 한해 적용. 실측 평가가 있는 선수는 건드리지 않는다.
"""
import json, os
BASE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(BASE, "data/players.json")
T = os.path.join(BASE, "data/teams.json")
players = json.load(open(P, encoding="utf-8"))

# ══════════ ② 학년 재확인 ══════════════════════════════════════════
G3_CONFIRMED = {  # 이름|학교 → KBSA 등록 포지션(세분)
 "김민훈|광주진흥고": "투수", "서원준|충암고": "투수", "민주홍|설악고": "투수",
 "서민준|김해고": "투수", "박현민|덕수고": "미지정", "김규민|덕수고": "투수",
 "곽동엽|서울자동차고": "투수", "박준성|인창고": "외야수", "조성철|라온고": "내야수",
 "설재민|덕수고": "포수", "강인규|청주고": "유격수", "김선우|북일고": "내야수",
 "이산|청원고": "외야수", "김건|진영고": "유격수", "김서준|상동고": "유격수",
 "김선빈|서울고": "유격수", "김건우|성남고": "유격수", "조희성|유신고": "중견수",
 "박지율|유신고": "좌익수", "배종윤|광주제일고": "외야수", "김지혁|라온고": "투수",
 "서성빈|부산고": "내야수", "엄준상|덕수고": "내야수",
}
# 3학년 명단에 없음 → 지명 대상 아님 (개별 조회로 2학년 확인분 포함)
NOT_G3 = {
 "전나엘|강릉고": "KBSA 개별 조회 결과 2학년 — 2028 드래프트 대상",
 "성세람|충암고": "KBSA 개별 조회 결과 2학년 — 2028 드래프트 대상",
 "신지호|충암고": "KBSA 개별 조회 결과 2학년 — 2028 드래프트 대상",
 "장근우|충암고": "KBSA 개별 조회 결과 2학년 — 2028 드래프트 대상",
 "한승우|유신고": "KBSA 2026 명단에 없음 — 지명 대상 확인 불가",
 "임고건|상원고": "KBSA 3학년 명단에 없음 — 지명 대상 확인 불가",
 "소재휘|유신고": "KBSA 3학년 명단에 없음 — 지명 대상 확인 불가",
}
fixed, dropped = [], []
for p in players:
    if p["type"] != "HS":
        continue
    key = f'{p["name"]}|{p.get("hs")}'
    if key in G3_CONFIRMED:
        p["kbsa"] = {"grade": 3, "pos": p["pos"], "ht": p.get("ht"), "wt": p.get("wt"),
                     "tb": (p.get("tb") or ""), "detail_pos": G3_CONFIRMED[key],
                     "src": "KBSA 2026 등록명단(재조회)"}
        p["note"] = p["note"].replace(
            "※KBSA 2026 등록명단 미등재 — 소속교 3학년 등록 인원이 비정상적으로 적어 "
            "협회 등록 누락 가능성 있음. 학년 확인 필요", "").strip(" /")
        if p["conf"] == "low":
            p["conf"] = "mid"
        fixed.append(p["name"])
    elif key in NOT_G3:
        p["eligible"] = False
        p["elig_note"] = NOT_G3[key]
        dropped.append(p["name"])
print(f"② 학년 확정 {len(fixed)}명 / 대상 제외 {len(dropped)}명 → {', '.join(dropped)}")

# ══════════ ④ 신체 기반 talent 사전확률 ═══════════════════════════
# 미평가 선수(conf low, perf 없음)만 대상. 기준선 + 신체/투타 프리미엄.
def prior(p):
    pos, ht, wt = p["pos"], p.get("ht"), p.get("wt")
    base = {"P": 58.0, "C": 57.0, "IF": 56.5, "OF": 56.0}[pos]
    if p["type"] == "COL":
        base -= 3.5                                   # 대졸 미평가 자원은 보수적으로
    if not ht:
        return None
    if pos == "P":
        base += max(-4.0, min(9.0, (ht - 182) * 0.65))    # 장신 우대
        base += max(-2.0, min(3.0, (wt - 84) * 0.10))
        if p.get("throws") == "L":
            base += 3.2                                    # 좌완 희소가치
        elif p.get("throws") == "S":
            base += 1.5                                    # 사이드암
    else:
        base += max(-3.0, min(5.0, (ht - 180) * 0.42))
        base += max(-2.5, min(4.0, (wt - 80) * 0.16))      # 파워 프록시
        tb = p.get("tb") or ""
        if "좌타" in tb: base += 1.4
        if "양타" in tb: base += 0.8
        if pos == "C":  base += 0.3                        # 포수 자원 희소
    return round(base, 1)

# ④ 미채택 — fm 11R A/B 결과 순번 상관이 ρ 0.641 → 0.429 로 악화. 코드는 보존하되 비활성.
APPLY_PHYSIQUE_PRIOR = False
n4 = 0
for p in (players if APPLY_PHYSIQUE_PRIOR else []):
    if p["conf"] == "high" or not p["eligible"]:
        continue
    perf = p.get("perf")
    # perf α가 0.15(현장 언급만)인 선수도 기반 scout이 선형 감쇠값이므로 함께 교체한다.
    # α ≥ 0.30 (실측 기록 보유)은 손대지 않는다.
    if perf and perf.get("alpha", 0) > 0.15:
        continue
    if not perf and p["conf"] == "mid" and p.get("scout", 0) >= 70:
        continue                                            # 개별 서술이 있는 상위 후보는 유지
    v = prior(p)
    if v is None:
        continue
    p["scout"] = v
    if perf:
        a = perf["alpha"]
        p["talent"] = round(v * (1 - a) + perf["score"] * a, 1)
    else:
        p["talent"] = v
    p["var"] = 8 if p.get("kbsa") not in (None, "absent") else 10
    n4 += 1
print(f"④ 신체 기반 사전확률 — {'적용 '+str(n4)+'명' if APPLY_PHYSIQUE_PRIOR else '미채택(A/B 결과 역효과)'}")

json.dump(players, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ══════════ ③ 포수 니즈 축소 + 투수 비중 상향 ═════════════════════
meta = json.load(open(T, encoding="utf-8"))
POS = ["P", "C", "IF", "OF"]
for t in meta["teams"]:
    r = t.get("roster") or {}
    c = r.get("catchers_registered", 6.5)
    # 기존: need_C += (6.5-c)*0.035  → 계수 0.015 로 축소 (재적용 위해 차분 보정)
    t["need"]["C"] = round(min(0.95, max(0.20, t["need"]["C"] - (6.5 - c) * 0.020)), 3)
    # 투수 비중 상향: 전 구단 공통 +0.07, 야수 -0.02씩
    t["need"]["P"] = round(min(0.95, t["need"]["P"] + 0.07), 3)
    for k in ("IF", "OF"):
        t["need"][k] = round(max(0.20, t["need"][k] - 0.02), 3)
    t["weight"] = {p: round(0.4 * t["tendency"][p] + 0.6 * t["need"][p], 3) for p in POS}
json.dump(meta, open(T, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("③ 포수 계수 0.035→0.015, 투수 니즈 +0.07 / 야수 −0.02 적용")
for t in sorted(meta["teams"], key=lambda x: x["pick_order"]):
    print(f"   {t['pick_order']:2d}. {t['id']:3s} {t['weight']}")
