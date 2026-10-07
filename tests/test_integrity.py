# -*- coding: utf-8 -*-
"""README "검증" 절의 무결성 테스트를 코드화: 총 110픽 / 중복 없음 / 팀별 픽 수 / 대졸 의무.

    python3 -m unittest discover -s tests -t .
"""
import os
import subprocess
import sys
import unittest
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import Draft, load  # noqa: E402

SEEDS = [1, 7, 2027, 31337, 99999]
PARAMS = [(14.0, 1.0), (8.0, 0.5), (20.0, 1.5)]  # (need_scale, noise)


class DraftIntegrityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.players, cls.meta = load()
        trades = cls.meta["pick_trades"]
        cls.expected = {
            t["id"]: 11 + sum(x["to"] == t["id"] for x in trades) - sum(x["from"] == t["id"] for x in trades)
            for t in cls.meta["teams"]
        }

    def _check(self, d):
        picks = d.picks
        self.assertEqual(len(picks), 110, "총 110픽")
        self.assertEqual(len({p["player"] for p in picks}), 110, "중복 지명 없음")
        self.assertEqual(sorted(p["overall"] for p in picks), list(range(1, 111)), "전체 순번 1..110")
        self.assertEqual(dict(Counter(p["team"] for p in picks)), self.expected, "팀별 픽 수 (트레이드 반영)")
        for tid in d.teams:
            self.assertTrue(any(d.board[x]["college_grad"] for x in d.rosters[tid]), f"{tid} 대졸 의무지명")
        eligible = {p["id"] for p in self.players}
        self.assertTrue(all(p["player"] in eligible for p in picks), "지명 대상(eligible) 선수만 지명")
        errs, _ = d.validate()
        self.assertEqual(errs, [])

    def test_param_grid_and_seeds(self):
        for need_scale, noise in PARAMS:
            for seed in SEEDS:
                with self.subTest(need_scale=need_scale, noise=noise, seed=seed):
                    d = Draft(self.players, self.meta, seed=seed, need_scale=need_scale, noise=noise)
                    d.run()
                    self._check(d)

    def test_pick_trade_is_exercised(self):
        d = Draft(self.players, self.meta, seed=2027)
        d.run()
        for t in self.meta["pick_trades"]:
            pick = next(p for p in d.picks if p["round"] == t["round"] and p["slot"] == t["slot"])
            self.assertEqual(pick["team"], t["to"])

    def test_same_seed_is_reproducible(self):
        a = Draft(self.players, self.meta, seed=42)
        b = Draft(self.players, self.meta, seed=42)
        a.run()
        b.run()
        self.assertEqual([p["player"] for p in a.picks], [p["player"] for p in b.picks])


class HtmlBuildTest(unittest.TestCase):
    def test_committed_html_matches_data(self):
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "build_html.py"), "--check"], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
