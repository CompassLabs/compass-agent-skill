#!/usr/bin/env python3
"""Regenerate AGENTS.md and GEMINI.md from the skill sources.

Both files are the skill for agents that read a single rules file: SKILL.md
without its frontmatter, followed by each reference file under an anchor.
Mentions of a reference file become links to its anchor, except inside code
fences. Run from anywhere:

    python3 scripts/generate_agents_md.py          # rewrite both files
    python3 scripts/generate_agents_md.py --check  # exit 1 if they are stale
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "compass"
REFERENCES = ("command-catalog", "error-recovery", "recipes", "signing")
OUTPUTS = ("AGENTS.md", "GEMINI.md")

_MENTION = re.compile(r"`(?:references/)?(" + "|".join(REFERENCES) + r")\.md`")


def _link_mentions(text: str) -> str:
    out: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        out.append(line if in_fence else _MENTION.sub(r"[\1](#\1)", line))
    return "\n".join(out)


def build() -> str:
    body = (SKILL / "SKILL.md").read_text(encoding="utf-8").split("---\n", 2)[2]
    for name in REFERENCES:
        content = (SKILL / "references" / f"{name}.md").read_text(encoding="utf-8")
        body += f'\n\n---\n\n<a id="{name}"></a>\n\n' + content
    return _link_mentions(body)


def main() -> int:
    text = build()
    if "--check" in sys.argv[1:]:
        stale = [n for n in OUTPUTS if (ROOT / n).read_text(encoding="utf-8") != text]
        if stale:
            print("stale: " + ", ".join(stale))
            return 1
        print("up to date")
        return 0
    for name in OUTPUTS:
        (ROOT / name).write_text(text, encoding="utf-8")
        print("wrote " + name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
