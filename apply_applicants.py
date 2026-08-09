# -*- coding: utf-8 -*-
"""
드래프트 참가신청자 명단 게이트
────────────────────────────────
2023 드래프트부터 졸업예정자 자동 대상이 폐지되고 **참가신청자에 한해서만** 지명 대상이 된다.
따라서 KBSA 고교 3학년 1,113명을 그대로 보드에 넣으면 안 되고,
KBO가 공표하는 참가신청자 명단과 교집합을 취해야 한다.

2027 드래프트 신청 일정
  - 특별 자격자(해외파·중퇴·독립리그 등): 2026-07-06 ~ 08-07 (마감)
  - 일반 지원자(고교·대학 졸업예정, 얼리): 2026-07-01 ~ 2026-08-22
  - 트라이아웃: 2026-09-01
  - 드래프트: 2026-09-21
→ 2026-08-09 현재 일반 지원자 접수 진행 중이라 확정 명단이 존재하지 않음.

사용법
  1) 신청자 명단이 공표되면 data/applicants.txt 에 한 줄씩 기록
         이름,학교            예) 하현승,부산고
     (학교는 부분일치 허용. '#'로 시작하는 줄은 주석)
  2) python3 apply_applicants.py
     - 명단에 있는 선수  → applied=True
     - 명단에 없는 선수  → applied=False, eligible=False (보드에서 제외)
     - 파일이 없으면     → applied=None (미확인). 전원 잠정 대상으로 유지
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(BASE, "data/players.json")
LIST = os.path.join(BASE, "data/applicants.txt")
players = json.load(open(P, encoding="utf-8"))

if not os.path.exists(LIST):
    for p in players:
        p["applied"] = None
    json.dump(players, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("data/applicants.txt 없음 → 전원 applied=None(미확인) 처리.")
    print("KBO 참가신청 마감 2026-08-22 이후 명단을 채우면 자동으로 게이트가 작동합니다.")
    raise SystemExit

entries = []
for line in open(LIST, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    parts = [x.strip() for x in line.split(",")]
    entries.append((parts[0], parts[1] if len(parts) > 1 else ""))

hit, miss = 0, []
for p in players:
    school = (p.get("hs") or "") + (p.get("univ") or "") + (p.get("indy") or "")
    ok = any(n == p["name"] and (not s or s in school) for n, s in entries)
    p["applied"] = ok
    if ok:
        hit += 1
    else:
        p["eligible"] = False
        p["elig_note"] = "드래프트 참가신청자 명단 미포함 — 지명 대상 아님"
        miss.append(f'{p["name"]}({school})')

json.dump(players, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"신청자 명단 {len(entries)}건 / 풀 내 매칭 {hit}명 / 미신청 처리 {len(miss)}명")
if miss:
    print("제외:", ", ".join(miss[:20]), "..." if len(miss) > 20 else "")
