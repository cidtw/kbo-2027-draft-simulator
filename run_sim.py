# -*- coding: utf-8 -*-
"""전체 시뮬레이션 실행 + 몬테카를로 지명 확률 보드 산출"""
import sys, json, os
from collections import defaultdict
from engine import load, Draft, school_label, POS_KR, tb_label

BASE = os.path.dirname(os.path.abspath(__file__))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 2027

players, meta = load()

# ── 대표 시나리오 1회 ─────────────────────────────────────────
d = Draft(players, meta, seed=SEED)
d.run()
errs, warns = d.validate()

# ── 몬테카를로 ────────────────────────────────────────────────
overall = defaultdict(list)
team_hit = defaultdict(lambda: defaultdict(int))
r1 = defaultdict(int)
for s in range(N):
    m = Draft(players, meta, seed=SEED * 100000 + s)
    m.run()
    for pk in m.picks:
        overall[pk["player"]].append(pk["overall"])
        team_hit[pk["player"]][pk["team"]] += 1
        if pk["round"] == 1:
            r1[pk["player"]] += 1

rows = []
for pid, lst in overall.items():
    p = d.board[pid]
    avg = sum(lst) / len(lst)
    best = min(lst)
    top = sorted(team_hit[pid].items(), key=lambda x: -x[1])[:2]
    rows.append({
        "id": pid, "name": p["name"], "pos": POS_KR[p["pos"]], "tb": tb_label(p), "school": school_label(p),
        "type": p["type"], "talent": p["talent"], "conf": p["conf"],
        "avg": round(avg, 1), "best": best, "picked_rate": round(len(lst) / N * 100, 1),
        "r1_rate": round(r1[pid] / N * 100, 1),
        "top_teams": [{"team": t, "pct": round(c / N * 100, 1)} for t, c in top],
    })
rows.sort(key=lambda x: x["avg"])
for i, r in enumerate(rows, 1):
    r["rank"] = i

with open(os.path.join(BASE, "out/board.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

md = [f"# 2027 KBO 신인 드래프트 예상 지명 시뮬레이션",
      f"\n> 대표 시나리오 seed={SEED} / 몬테카를로 {N}회 기준\n",
      "## 1. 전체 시뮬레이션 결과\n", d.table_markdown(),
      "\n## 2. 예상 지명 순위 보드 (몬테카를로 평균 전체 순번 상위 40인)\n",
      "| 순 | 선수 | 포지션 | 투타 | 출신 | 평균순번 | 최고 | 1R확률 | 지명확률 | 유력구단 |",
      "|:---:|:---|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---|"]
for r in rows[:40]:
    tt = ", ".join(f'{x["team"]} {x["pct"]}%' for x in r["top_teams"])
    md.append(f'| {r["rank"]} | {r["name"]} | {r["pos"]} | {r["tb"]} | {r["school"]} | {r["avg"]} | '
              f'{r["best"]} | {r["r1_rate"]}% | {r["picked_rate"]}% | {tt} |')
md += ["\n## 3. 검증", f"- 오류: {errs or '없음'}", f"- 경고: {warns or '없음'}",
       f"- 총 픽: {len(d.picks)} / 지명대상 선수풀: {len(players)}명",
       f"- 지명권 이관 반영: {meta['pick_trades']}"]

with open(os.path.join(BASE, "out/simulation.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print("\n".join(md[:6]))
print(f"\n...board.json / simulation.md 생성 완료 (몬테카를로 {N}회)")
print("검증:", errs or "오류 없음", warns or "")
