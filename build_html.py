# -*- coding: utf-8 -*-
"""template.html 의 __DATA__ 자리에 data/*.json 을 주입해 KBO_2027_draft_simulator.html 을 만든다.

    python3 build_html.py          # HTML 재생성
    python3 build_html.py --check  # 커밋된 HTML이 data/ 와 일치하는지만 확인 (불일치 시 exit 1)

주입 데이터: {players: data/players.json, teams/trades/rules: data/teams.json}
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(BASE, "template.html")
OUT = os.path.join(BASE, "KBO_2027_draft_simulator.html")
PLACEHOLDER = "__DATA__"


def build_payload():
    with open(os.path.join(BASE, "data/players.json"), encoding="utf-8") as f:
        players = json.load(f)
    with open(os.path.join(BASE, "data/teams.json"), encoding="utf-8") as f:
        meta = json.load(f)
    return {"players": players, "teams": meta["teams"], "trades": meta["pick_trades"], "rules": meta["rules"]}


def render():
    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    if template.count(PLACEHOLDER) != 1:
        raise SystemExit(f"template.html 에 {PLACEHOLDER} 가 정확히 1개 있어야 합니다")
    data = json.dumps(build_payload(), ensure_ascii=False, separators=(",", ":"))
    # 데이터 안의 "</script>" 가 스크립트 블록을 닫지 않도록 이스케이프 (JSON 의미는 동일)
    data = data.replace("</", "<\\/")
    return template.replace(PLACEHOLDER, data)


def main(argv):
    html = render()
    if "--check" in argv:
        with open(OUT, encoding="utf-8") as f:
            current = f.read()
        if current != html:
            print("KBO_2027_draft_simulator.html 이 data/ 와 다릅니다 → python3 build_html.py 로 재생성하세요")
            return 1
        print("KBO_2027_draft_simulator.html 최신 상태")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {os.path.relpath(OUT, BASE)} ({len(html.encode('utf-8')) / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
