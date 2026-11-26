#!/usr/bin/env python3
"""Check a public blog post before publishing.

Errors (exit 1): CJK ideographs (hanja), emoji, IPv4 addresses, deny-list terms,
unbalanced code fences, missing front matter keys.
Warnings (exit 0): prose length outside the target range.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

HANJA = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]"
)
IPV4 = re.compile(r"(?<![\w.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\w.])")
FENCE = re.compile(r"^\s*(```|~~~)")
REQUIRED_KEYS = ("title", "tags", "summary")
PROSE_MIN, PROSE_MAX = 40, 150


def split_front_matter(lines: List[str]) -> Tuple[List[str], int]:
    """Return (front matter lines, index where body starts)."""
    if not lines or lines[0].strip() != "---":
        return [], 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], i + 1
    return [], 0


def load_deny(terms: List[str], deny_file: Optional[str]) -> List[str]:
    out = [t.strip() for t in terms if t.strip()]
    if deny_file:
        for raw in Path(deny_file).expanduser().read_text(encoding="utf-8").splitlines():
            term = raw.strip()
            if term and not term.startswith("#"):
                out.append(term)
    return out


def check(text: str, deny: List[str]) -> Tuple[List[str], List[str], int]:
    errors: List[str] = []
    warnings: List[str] = []
    lines = text.splitlines()

    front, body_start = split_front_matter(lines)
    if not front:
        errors.append("front matter 없음: 첫 줄이 '---'인 머리말이 필요합니다")
    else:
        keys = {ln.split(":", 1)[0].strip() for ln in front if ":" in ln}
        for key in REQUIRED_KEYS:
            if key not in keys:
                errors.append(f"front matter에 '{key}' 없음")

    fences = 0
    in_code = False
    prose = 0
    for no, line in enumerate(lines, start=1):
        if HANJA.search(line):
            errors.append(f"{no}: 한자 '{HANJA.search(line).group()}'")
        if EMOJI.search(line):
            errors.append(f"{no}: 이모지 U+{ord(EMOJI.search(line).group()):04X}")
        for m in IPV4.finditer(line):
            if all(0 <= int(part) <= 255 for part in m.groups()):
                errors.append(f"{no}: IPv4 '{m.group()}'")
        lowered = line.lower()
        for term in deny:
            if term.lower() in lowered:
                errors.append(f"{no}: 금지어 '{term}'")
        if FENCE.match(line):
            fences += 1
            in_code = not in_code
            continue
        if no > body_start and not in_code and line.strip():
            prose += 1

    if fences % 2:
        errors.append(f"코드 블록 짝이 맞지 않음: 펜스 {fences}개")
    if prose > PROSE_MAX:
        warnings.append(f"본문 {prose}줄: {PROSE_MAX}줄 초과. 이론부터 덜어 내세요")
    elif prose < PROSE_MIN:
        warnings.append(f"본문 {prose}줄: {PROSE_MIN}줄 미만. 단계가 빠졌는지 확인하세요")
    return errors, warnings, prose


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="공개 블로그 글 사전 점검")
    parser.add_argument("post", help="검사할 Markdown 파일")
    parser.add_argument("--deny", action="append", default=[], help="금지어(여러 번 지정 가능)")
    parser.add_argument("--deny-file", help="금지어 목록 파일(한 줄에 하나, #은 주석)")
    args = parser.parse_args(argv)

    text = Path(args.post).read_text(encoding="utf-8")
    errors, warnings, prose = check(text, load_deny(args.deny, args.deny_file))

    for e in errors:
        print(f"ERROR {e}")
    for w in warnings:
        print(f"WARN  {w}")
    print(f"본문(코드·머리말 제외) {prose}줄, 오류 {len(errors)}건, 경고 {len(warnings)}건")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
