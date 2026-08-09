# -*- coding: utf-8 -*-
"""
2027 KBO 신인 드래프트 시뮬레이션 엔진
- Z-shape 11라운드 × 10구단 = 110픽
- 구단별 지명 성향(tendency) + 뎁스 니즈(need) + BPA 성향 + 스카우팅 편차 반영
- 제약: 대졸 의무지명 1명, 지명권 트레이드 반영, 지명 대상 제외 선수 배제
"""
import json, os, random
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
POS = ["P", "C", "IF", "OF"]


def load():
    with open(os.path.join(BASE, "data/players.json"), encoding="utf-8") as f:
        players = [p for p in json.load(f) if p["eligible"]]
    with open(os.path.join(BASE, "data/teams.json"), encoding="utf-8") as f:
        meta = json.load(f)
    return players, meta


def school_label(p):
    """출력용 출신 표기 규칙"""
    if p["type"] == "OVERSEAS":
        parts = [x for x in (p.get("hs"), p.get("univ"), p.get("foreign")) if x]
        return " - ".join(parts)
    if p["type"] == "INDY":
        parts = [x for x in (p.get("univ"), p.get("indy")) if x]
        return " - ".join(parts)
    if p["type"] == "COL_EARLY":
        return f'{p.get("hs") or "?"} - {p.get("univ")} (얼리)'
    if p["type"] == "COL":
        return f'{p.get("hs") + " - " if p.get("hs") else ""}{p.get("univ")}'
    return p.get("hs") or "?"


POS_KR = {"P": "투수", "C": "포수", "IF": "내야수", "OF": "외야수"}


def tb_label(p):
    """투타유형. 공식값이 있으면 그대로, 투구 손만 알면 '우투' 형태, 없으면 '-'"""
    return p.get("tb") or "-"


def cell(p):
    return (f'{p["name"]}<br />({school_label(p)} - {POS_KR[p["pos"]]} · {tb_label(p)})')


class Draft:
    def __init__(self, players, meta, seed=None, need_scale=14.0, noise=1.0):
        self.rng = random.Random(seed)
        self.meta = meta
        self.rules = meta["rules"]
        self.teams = {t["id"]: t for t in meta["teams"]}
        self.order = [t["id"] for t in sorted(meta["teams"], key=lambda x: x["pick_order"])]
        self.trades = {(t["round"], t["slot"]): t for t in meta["pick_trades"]}
        self.need_scale = need_scale
        self.noise = noise
        self.board = {p["id"]: dict(p) for p in players}
        # 구단이 인식하는 재능치(스카우팅 편차) — 구단별로 다르게 본다
        # 평가가 확립된 선수(var 작음)일수록 구단 간 견해차가 작다
        self.view = {tid: {pid: p["talent"] + self.rng.gauss(0, p["var"] * 0.35)
                           for pid, p in self.board.items()} for tid in self.teams}
        self.available = set(self.board)
        self.rosters = defaultdict(list)
        self.picks = []
        self.dyn_need = {tid: dict(self.teams[tid]["weight"]) for tid in self.teams}

    # ── 픽 소유 구단 ──────────────────────────────────────────
    def owner(self, rnd, slot):
        tr = self.trades.get((rnd, slot))
        return (tr["to"] if tr else self.order[slot - 1]), (tr if tr else None)

    # ── 점수 계산 ────────────────────────────────────────────
    def score(self, tid, pid, rnd):
        t = self.teams[tid]
        p = self.board[pid]
        talent = self.view[tid][pid]
        # 라운드가 갈수록 BPA→니즈 중심으로 이동
        need_w = self.need_scale * (0.35 + 0.09 * (rnd - 1)) * (1.3 - t["bpa"])
        s = talent + need_w * (self.dyn_need[tid][p["pos"]] - 0.5) * 2
        # 고졸/대졸 선호
        if p["type"] == "HS":
            s += (t["hs_pref"] - 0.5) * 8
        elif p["type"] in ("COL", "COL_EARLY"):
            s += (0.5 - t["hs_pref"]) * 8
        else:  # 해외복귀/독립 등 특수 케이스는 보수적
            s += (0.5 - t["hs_pref"]) * 8 - 4
        # 리스크(평가 편차) 감수 성향
        s += (t["risk"] - 0.5) * p["var"] * 0.6
        # 대졸 의무지명 압박: 남은 라운드가 적을수록 대졸 가산
        if p["college_grad"] and not self._has_grad(tid):
            left = self.rules["rounds"] - rnd
            if left <= 3:
                s += (4 - left) * 18
        # 당일 변수(돌발 픽): 평가 불확실성이 큰 선수일수록 크게 흔들린다
        s += self.rng.gauss(0, (0.6 + 0.30 * p["var"]) * self.noise)
        return s

    def _has_grad(self, tid):
        return any(self.board[x]["college_grad"] for x in self.rosters[tid])

    def _grads_left(self):
        return sorted(x for x in self.available if self.board[x]["college_grad"])

    # ── 한 픽 실행 ───────────────────────────────────────────
    def best_for(self, tid, rnd, topn=1):
        # ※ set 순회 순서는 파이썬 문자열 해시 랜덤화 때문에 프로세스마다 달라진다.
        #    score()가 후보마다 RNG를 소비하므로 정렬하지 않으면 같은 시드도 재현되지 않는다.
        cands = sorted(self.available)
        if rnd == self.rules["rounds"] and not self._has_grad(tid):
            g = self._grads_left()
            if g:
                cands = g
        ranked = sorted(cands, key=lambda pid: -self.score(tid, pid, rnd))
        return ranked[:topn] if topn > 1 else ranked[0]

    def commit(self, rnd, slot, tid, pid, by="AI"):
        self.available.discard(pid)
        self.rosters[tid].append(pid)
        p = self.board[pid]
        # 같은 포지션을 뽑으면 해당 니즈 감소
        self.dyn_need[tid][p["pos"]] = max(0.05, self.dyn_need[tid][p["pos"]] - 0.16)
        overall = (rnd - 1) * 10 + slot
        self.picks.append({"round": rnd, "slot": slot, "overall": overall,
                           "team": tid, "player": pid, "by": by})
        return self.picks[-1]

    def run(self, stop_at=None, user_team=None):
        """stop_at: (round, slot) 직전까지 진행. user_team 차례에서 멈추려면 sim_until_user 사용"""
        for rnd in range(1, self.rules["rounds"] + 1):
            for slot in range(1, self.rules["teams"] + 1):
                if stop_at and (rnd, slot) == stop_at:
                    return
                tid, _ = self.owner(rnd, slot)
                self.commit(rnd, slot, tid, self.best_for(tid, rnd))

    # ── 결과 출력 ────────────────────────────────────────────
    def table_markdown(self):
        cols = self.order
        head = "| 라운드 | " + " | ".join(cols) + " |"
        align = "|" + ":---:|" * (len(cols) + 1)
        grid = defaultdict(dict)
        for pk in self.picks:
            grid[pk["round"]][pk["slot"]] = pk
        lines = [head, align]
        for rnd in range(1, self.rules["rounds"] + 1):
            row = [f"**{rnd}R**"]
            for slot in range(1, 11):
                pk = grid[rnd].get(slot)
                if not pk:
                    row.append("-")
                    continue
                p = self.board[pk["player"]]
                txt = cell(p)
                tr = self.trades.get((rnd, slot))
                if tr:
                    txt += f'<br />※{tr["to"]} 행사'
                row.append(txt)
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    def validate(self):
        errs, warns = [], []
        if len(self.picks) != 110:
            errs.append(f"총 픽 수 {len(self.picks)} ≠ 110")
        if len(set(p["player"] for p in self.picks)) != len(self.picks):
            errs.append("중복 지명 발생")
        for tid in self.teams:
            n = len(self.rosters[tid])
            expect = 11 + sum(1 for t in self.meta["pick_trades"] if t["to"] == tid) \
                        - sum(1 for t in self.meta["pick_trades"] if t["from"] == tid)
            if n != expect:
                errs.append(f"{tid} 지명 수 {n} ≠ 기대 {expect}")
            if not self._has_grad(tid):
                errs.append(f"{tid} 대졸 의무지명 위반")
        for tid in self.teams:
            c = sum(1 for x in self.rosters[tid] if self.board[x]["pos"] == "P")
            if c >= 10:
                warns.append(f"{tid} 투수 {c}명 편중")
        return errs, warns


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 2027
    players, meta = load()
    d = Draft(players, meta, seed=seed)
    d.run()
    errs, warns = d.validate()
    print(f"# 2027 KBO 신인 드래프트 예상 지명 시뮬레이션 (seed={seed})\n")
    print(d.table_markdown())
    print("\n## 검증")
    print("- 오류:", errs or "없음")
    print("- 경고:", warns or "없음")
