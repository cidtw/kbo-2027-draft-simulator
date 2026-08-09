# -*- coding: utf-8 -*-
"""
2027 KBO 신인 드래프트 - 구단 프로파일 빌더
- order: 2025 시즌 최종순위 역순 (사용자 제공 확정값)
- tendency: 2026 신인 드래프트 실제 지명 포지션 분포(국제뉴스 지명결과 기사)로부터 산출한 '지명 성향'
- need: 2026시즌 기준 1군/팜 뎁스 약점 추정치 (※ 추정. 구단 공식 자료 아님)
- 유효 가중치 = 0.4*tendency + 0.6*need
"""
import json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# 2026 신인 드래프트 실제 지명 포지션 카운트 (P/C/IF/OF)
D26 = {
    "키움": (8, 1, 3, 0), "두산": (4, 0, 4, 3), "KIA": (4, 1, 2, 3), "롯데": (6, 1, 3, 1),
    "kt": (5, 1, 3, 1), "NC": (6, 1, 4, 2), "삼성": (9, 1, 1, 0), "SSG": (6, 0, 1, 3),
    "한화": (3, 0, 4, 3), "LG": (6, 1, 3, 1),
}

# 뎁스 약점 추정 (0~1, 높을수록 급함) + 근거
NEED = {
    "키움": ((0.55, 0.50, 0.60, 0.70), "정현우·박준현 등 투수 상위픽 축적 완료 → 야수 코어 확보가 다음 과제"),
    "두산": ((0.75, 0.80, 0.50, 0.55), "주전 포수 노쇠화·선발 뎁스 부족. 안방과 마운드 동시 리빌딩 필요"),
    "KIA": ((0.80, 0.70, 0.50, 0.45), "선발진 노쇠화 및 포수 세대교체 지연"),
    "롯데": ((0.60, 0.80, 0.65, 0.50), "고질적 포수 취약 + 내야 세대교체 미완"),
    "kt": ((0.60, 0.70, 0.50, 0.70), "베테랑 포수 이후 대안 부재, 외야 자원 고령화"),
    "NC": ((0.85, 0.45, 0.50, 0.55), "마운드 뎁스 급감. 3R 지명권 2장 보유로 투수 물량 확보 가능"),
    "삼성": ((0.60, 0.50, 0.75, 0.60), "최근 드래프트 투수 극단 편중 → 야수 팜 고갈, 내야 보강 시급"),
    "SSG": ((0.60, 0.50, 0.80, 0.70), "코너 내야/외야 핵심 타자 노쇠화가 가장 뚜렷"),
    "한화": ((0.45, 0.70, 0.70, 0.65), "리그 최상급 영건 선발진 보유 → 야수 쪽으로 무게중심 이동"),
    "LG": ((0.65, 0.60, 0.55, 0.55), "전 포지션 균형. 마지막 순번이라 BPA 성향 강함"),
}

# 고졸 선호도(0~1), 리스크 감수(0~1), BPA 성향(0~1: 높을수록 팀니즈 무시하고 최고 재능)
STYLE = {
    "키움": (0.85, 0.75, 0.80), "두산": (0.75, 0.50, 0.55), "KIA": (0.80, 0.55, 0.60),
    "롯데": (0.80, 0.60, 0.55), "kt": (0.75, 0.45, 0.60), "NC": (0.75, 0.60, 0.55),
    "삼성": (0.85, 0.55, 0.50), "SSG": (0.80, 0.50, 0.60), "한화": (0.80, 0.65, 0.55),
    "LG": (0.75, 0.50, 0.70),
}

ORDER = [("키움", "키움 히어로즈", 10), ("두산", "두산 베어스", 9), ("KIA", "KIA 타이거즈", 8),
         ("롯데", "롯데 자이언츠", 7), ("kt", "kt wiz", 6), ("NC", "NC 다이노스", 5),
         ("삼성", "삼성 라이온즈", 4), ("SSG", "SSG 랜더스", 3), ("한화", "한화 이글스", 2),
         ("LG", "LG 트윈스", 1)]

POS = ["P", "C", "IF", "OF"]
teams = []
for idx, (short, full, rank) in enumerate(ORDER, start=1):
    cnt = D26[short]
    tot = sum(cnt)
    # 성향: 실제 지명 비중을 포지션별 리그 평균 비중 대비로 정규화
    league = [0.55, 0.07, 0.24, 0.14]
    tend = {}
    for p, c, lg in zip(POS, cnt, league):
        share = c / tot
        tend[p] = round(min(1.0, max(0.0, 0.5 + (share - lg) * 1.6)), 3)
    need_vals, rationale = NEED[short]
    need = {p: v for p, v in zip(POS, need_vals)}
    weight = {p: round(0.4 * tend[p] + 0.6 * need[p], 3) for p in POS}
    hs_pref, risk, bpa = STYLE[short]
    teams.append({
        "id": short, "name": full, "pick_order": idx, "rank2025": rank,
        "d26_counts": {p: c for p, c in zip(POS, cnt)},
        "tendency": tend, "need": need, "weight": weight,
        "hs_pref": hs_pref, "risk": risk, "bpa": bpa,
        "rationale": rationale,
    })

# 지명권 이관: 2025-11-25 박세혁(NC) ↔ 2027 3R 지명권(삼성) 트레이드
pick_trades = [{
    "round": 3, "slot": 7, "from": "삼성", "to": "NC",
    "note": "2025-11-25 박세혁 ↔ 2027 3R 지명권 트레이드 (3R 7번 = 전체 27번). "
            "※ 입력값의 '전체 37번'은 4R 7번에 해당하므로 3R 기준인 27번으로 반영"
}]

rules = {
    "rounds": 11,
    "teams": 10,
    "format": "Z-shape (매 라운드 1→10 동일 순서)",
    "college_grad_mandatory": 1,
    "college_grad_note": "2019년 신설. 대졸(졸업예정) 최소 1명 지명 의무. 대학 얼리 신청자는 카운트되지 않음. "
                         "위반 시 제재금 + 익년도 1R 지명권 박탈",
    "early_draft": "3·4년제 대학 2학년 수료자 대상. 고졸 지명 거부 후 대학 진학자는 대상 아님",
    "rights_validity": "지명권 효력 2년",
    "draft_date": "2026-09-21 (2027 신인 드래프트)",
}

with open(os.path.join(OUT, "teams.json"), "w", encoding="utf-8") as f:
    json.dump({"teams": teams, "pick_trades": pick_trades, "rules": rules}, f,
              ensure_ascii=False, indent=1)

for t in teams:
    print(f"{t['pick_order']:2d}. {t['id']:3s} weight={t['weight']}  bpa={t['bpa']}")
