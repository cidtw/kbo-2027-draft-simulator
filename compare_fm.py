# -*- coding: utf-8 -*-
"""
내 시뮬레이터 vs fmkorea 유저 모의드래프트 교차검증
────────────────────────────────────────────────
입력
  data/fm_mock.txt   fmkorea 결과 (라운드별 10명, @alias/@meta 지시자 지원)
  out/board.json     내 몬테카를로 보드 (run_sim.py 산출)
  data/players.json  선수풀

산출
  콘솔 리포트 + out/fm_compare.json (지표 스냅샷 — 보정 전후 비교용)

라운드 수는 fm_mock.txt에 들어온 만큼 자동으로 맞춰 비교한다(5R이든 11R이든).
같은 시드/파라미터로 내 시뮬을 돌려 동일 라운드까지만 잘라 대조한다.
"""
import json, os, sys, statistics as st
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
ORDER = ["키움", "두산", "KIA", "롯데", "kt", "NC", "삼성", "SSG", "한화", "LG"]
POSKR = {"P": "투수", "C": "포수", "IF": "내야수", "OF": "외야수"}
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 2027

# ── fm_mock.txt 파싱 ──────────────────────────────────────────────
path = os.path.join(BASE, "data/fm_mock.txt")
alias, meta, FM = {}, {}, {}
for raw in open(path, encoding="utf-8"):
    line = raw.split("#")[0].strip()
    if not line:
        continue
    if line.startswith("@alias"):
        k, v = line.replace("@alias", "").strip().split("=")
        alias[k.strip()] = v.strip()
    elif line.startswith("@meta"):
        k, v = line.replace("@meta", "").strip().split("=", 1)
        meta[k.strip()] = v.strip()
    elif line[0].isdigit() and "R:" in line:
        rnd = int(line.split("R:")[0])
        names = [x.strip() for x in line.split("R:", 1)[1].split(",")]
        FM[rnd] = [alias.get(n, n) for n in names]   # '이름(학교)' 표기 허용

ROUNDS = max(FM) if FM else 0
NPICK = sum(len([x for x in v if x != "-"]) for v in FM.values())
print("=" * 66)
print(f"교차검증  fmkorea {ROUNDS}R {NPICK}픽  ({meta.get('출처','')} / {meta.get('기준일','')})")
print("=" * 66)

# ── 내 시뮬 실행 (동일 라운드까지) ────────────────────────────────
from engine import load, Draft
players, tmeta = load()
pool = {p["name"]: p for p in players}
d = Draft(players, tmeta, seed=SEED)
d.run()
MINE = {}
for pk in d.picks:
    if pk["round"] <= ROUNDS:
        MINE.setdefault(pk["round"], {})[pk["slot"]] = (d.board[pk["player"]]["name"], pk["team"])

board = {r["name"]: r for r in json.load(open(os.path.join(BASE, "out/board.json"), encoding="utf-8"))}

def split_school(tok):
    """'이현민(마산고)' → ('이현민','마산고')"""
    if "(" in tok and tok.endswith(")"):
        n, s = tok[:-1].split("(", 1)
        return n.strip(), s.strip()
    return tok, None

def resolve(name, school):
    """동명이인은 학교로 구분. 학교 미지정이면 첫 매칭."""
    cands = [p for p in players if p["name"] == name]
    if school:
        c2 = [p for p in cands if school in ((p.get("hs") or "") + (p.get("univ") or "") + (p.get("indy") or ""))]
        if c2: return c2[0]
    return cands[0] if cands else None

def flat_mine():
    out = {}
    for rnd, slots in MINE.items():
        for slot, (nm, team) in slots.items():
            k = nm
            i = 2
            while k in out: k = f"{nm}#{i}"; i += 1
            out[k] = {"name": nm, "school": None, "round": rnd, "slot": slot,
                      "overall": (rnd - 1) * 10 + slot, "team": team}
    return out

def flat_fm():
    out = {}
    for rnd, names in FM.items():
        for slot, tok in enumerate(names, 1):
            if tok == "-":
                continue
            nm, sc = split_school(tok)
            k = nm
            i = 2
            while k in out: k = f"{nm}#{i}"; i += 1
            out[k] = {"name": nm, "school": sc, "round": rnd, "slot": slot,
                      "overall": (rnd - 1) * 10 + slot,
                      "team": "NC" if (rnd, slot) == (3, 7) else ORDER[slot - 1]}
    return out

mine, fm = flat_mine(), flat_fm()
# 이름 기준 교집합 (동명이인은 등장 순서대로 1:1 대응)
from collections import defaultdict as _dd
_mn = _dd(list); _fn = _dd(list)
for k, v in mine.items(): _mn[v["name"]].append(k)
for k, v in fm.items():   _fn[v["name"]].append(k)
PAIR = {}   # fm key → mine key
for nm in set(_mn) & set(_fn):
    for a, b in zip(sorted(_fn[nm], key=lambda k: fm[k]["overall"]),
                    sorted(_mn[nm], key=lambda k: mine[k]["overall"])):
        PAIR[a] = b
common = set(PAIR)
R = {}

# [1] 선수풀 커버리지
missing = [fm[k]["name"] for k in fm if not resolve(fm[k]["name"], fm[k]["school"])]
R["pool_coverage"] = round((len(fm) - len(missing)) / len(fm) * 100, 1)
print(f"\n[1] 선수풀 커버리지  {len(fm)-len(missing)}/{len(fm)} = {R['pool_coverage']}%")
if missing:
    print(f"    미보유: {', '.join(missing)}")

# [2] 집합 재현율
R["recall"] = round(len(common) / len(fm) * 100, 1)
print(f"\n[2] 집합 재현율  {len(common)}/{len(fm)} = {R['recall']}%")
print(f"    내 시뮬만: {', '.join(sorted(set(mine)-common, key=lambda n: mine[n]['overall']))}")
print(f"    fm만    : {', '.join(sorted(set(fm)-common, key=lambda n: fm[n]['overall']))}")

# [3] 라운드별
print("\n[3] 라운드별 재현율")
R["by_round"] = {}
for r in range(1, ROUNDS + 1):
    a = {mine[k]["name"] for k in mine if mine[k]["round"] == r}
    b = {fm[k]["name"] for k in fm if fm[k]["round"] == r}
    fmall = {fm[k]["name"] for k in fm}; mnall = {mine[k]["name"] for k in mine}
    R["by_round"][r] = [len(a & fmall), len(b & mnall), len(a & b)]
    print(f"    {r:2d}R  내→fm {len(a&fmall):2d}/10   fm→내 {len(b&mnall):2d}/10   동일라운드 {len(a&b):2d}/10")

# [4] 픽 단위
exact = [k for k in common if mine[PAIR[k]]["overall"] == fm[k]["overall"]]
same_team = [k for k in common if mine[PAIR[k]]["team"] == fm[k]["team"]]
within1 = [k for k in common if abs(mine[PAIR[k]]["round"] - fm[k]["round"]) <= 1]
R.update(exact=len(exact), same_team=len(same_team),
         within1=round(len(within1) / max(1, len(common)) * 100, 1))
print(f"\n[4] 픽 단위 (교집합 {len(common)}명)")
print(f"    완전 일치 {len(exact)} · 구단 일치 {len(same_team)} · ±1R 이내 {len(within1)} ({R['within1']}%)")

# [5] 순번 상관
def rank(v):
    s = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v)
    for i, idx in enumerate(s): r[idx] = i + 1
    return r
def spearman(x, y):
    n = len(x)
    if n < 3: return float("nan")
    rx, ry = rank(x), rank(y)
    return 1 - 6 * sum((a - b) ** 2 for a, b in zip(rx, ry)) / (n * (n * n - 1))
xs = [mine[PAIR[k]]["overall"] for k in common]; ys = [fm[k]["overall"] for k in common]
R["rho_seed"] = round(spearman(xs, ys), 3)
R["mae"] = round(st.mean(abs(a - b) for a, b in zip(xs, ys)), 1) if common else None
print(f"\n[5] 순번 상관(단일 시드 {SEED})  ρ={R['rho_seed']}  MAE={R['mae']}픽")

# [6] 몬테카를로 보드 대조
pairs = [(board[fm[k]["name"]]["avg"], fm[k]["overall"], fm[k]["name"])
         for k in fm if fm[k]["name"] in board]
if len(pairs) >= 3:
    R["rho_mc"] = round(spearman([p[0] for p in pairs], [p[1] for p in pairs]), 3)
    print(f"\n[6] 몬테카를로 평균순번 vs fm 순번  n={len(pairs)}  ρ={R['rho_mc']}")
    diff = sorted(pairs, key=lambda x: -(x[0] - x[1]))
    print("    과소평가 top5:", ", ".join(f"{n}({a:.0f}→{f})" for a, f, n in diff[:5]))
    print("    과대평가 top5:", ", ".join(f"{n}({a:.0f}→{f})" for a, f, n in diff[-5:][::-1]))
    R["under"] = [[n, round(a, 1), f] for a, f, n in diff[:8]]
    R["over"] = [[n, round(a, 1), f] for a, f, n in diff[-8:][::-1]]
    top = [k for k, _ in sorted(board.items(), key=lambda kv: kv[1]["avg"])[:len(fm)]]
    R["mc_topN_overlap"] = len(set(top) & {fm[k]["name"] for k in fm})
    print(f"    몬테카를로 상위 {len(fm)} vs fm {len(fm)} 교집합: {R['mc_topN_overlap']}/{len(fm)}")

# [7] 포지션·유형 배분
def mix(tbl, key):
    c = Counter()
    for k in tbl:
        p = resolve(tbl[k]["name"], tbl[k].get("school"))
        if p: c[POSKR[p["pos"]] if key == "pos" else p["type"]] += 1
    return c
pm, pf = mix(mine, "pos"), mix(fm, "pos")
R["pos_mine"] = dict(pm); R["pos_fm"] = dict(pf)
print(f"\n[7] 포지션  내 시뮬 투{pm['투수']}/포{pm['포수']}/내{pm['내야수']}/외{pm['외야수']}"
      f"   |   fm 투{pf['투수']}/포{pf['포수']}/내{pf['내야수']}/외{pf['외야수']}")
tm, tf = mix(mine, "type"), mix(fm, "type")
print(f"[8] 유형    내 시뮬 고졸{tm['HS']}/대졸{tm['COL']}   |   fm 고졸{tf['HS']}/대졸{tf['COL']}")

# [9] KBSA 미등재 교차판정
fm_names = {fm[k]["name"] for k in fm}
absent = [mine[k]["name"] for k in mine
          if (pool.get(mine[k]["name"]) or {}).get("kbsa") == "absent"]
grpA = [n for n in absent if n in fm_names]
grpB = [n for n in absent if n not in fm_names]
R["kbsa_absent_A"] = grpA; R["kbsa_absent_B"] = grpB
print(f"\n[9] KBSA 미등재 교차판정 (내 픽 {len(absent)}명)")
print(f"    A. fm도 지명 → 협회 등록 누락(3학년 확정적): {', '.join(grpA) or '-'}")
print(f"    B. fm도 미지명 → 2학년 의심            : {', '.join(grpB) or '-'}")

# [10] 구단별
print("\n[10] 구단별 교집합")
for t in ORDER:
    a = {mine[k]["name"] for k in mine if mine[k]["team"] == t}
    b = {fm[k]["name"] for k in fm if fm[k]["team"] == t}
    print(f"    {t:4s} {len(a&b)}/{len(b)}  {'· '+', '.join(sorted(a&b)) if a&b else ''}")

R["seed"] = SEED; R["rounds"] = ROUNDS; R["meta"] = meta
json.dump(R, open(os.path.join(BASE, "out/fm_compare.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n→ out/fm_compare.json 저장 (보정 전후 비교용 스냅샷)")
print("=" * 66)
