#!/usr/bin/env python3
"""Read-only checks for a Personal IP Vault; standard library, Python 3.9+."""

import argparse
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit


DEFAULT_EXCLUDES = (
    "10-個人核心/私密身份",
    "60-學習與反思/02-私密反思",
    "00-收件箱/原始文件",
    "90-Archive",
)
DEFAULT_REQUIRED = ("AGENTS.md", "INDEX.md", "VAULT-STATUS.md")
# ponytail: checks ordinary inline links; Wiki/reference syntax fails for manual review.
# Use a CommonMark parser if full Markdown syntax becomes a maintained requirement.
LINK = re.compile(
    r"""!?\[[^\]\n]*\]\(\s*(<[^>\n]+>|[^\s)]+)(?:\s+(?:"[^"]*"|'[^']*'))?\s*\)"""
)


def relative_paths(values):
    result = []
    for value in values:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or path == Path("."):
            raise ValueError("Expected a non-root relative path without '..'.")
        result.append(path.as_posix().rstrip("/"))
    return tuple(result)


def is_excluded(relative, excludes):
    value = relative.as_posix()
    return any(value == item or value.startswith(item + "/") for item in excludes)


def read_nonprivate(path):
    """Inspect only the header before deciding whether to read a note's body."""
    with path.open("rb") as stream:
        first = stream.readline()
        clean = first[3:] if first.startswith(b"\xef\xbb\xbf") else first
        if clean.strip() != b"---":
            return (first + stream.read()).decode("utf-8-sig")
        header = [first]
        for _ in range(100):
            line = stream.readline()
            if not line:
                break
            header.append(line)
            if re.fullmatch(
                rb"""visibility:\s*(?:"private"|'private'|private)\s*(?:#.*)?""",
                line.strip(),
            ):
                return None
            if line.strip() == b"---":
                return (b"".join(header) + stream.read()).decode("utf-8-sig")
    raise ValueError("Unclosed or oversized frontmatter.")


def prose_only(text):
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(\x60{3,}|~{3,})(.*)$", line)
        if marker:
            token, tail = marker.groups()
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not tail.strip():
                fence = None
            continue
        if fence is None:
            lines.append(re.sub(r"\x60+[^\x60]*\x60+", "", line))
    return "\n".join(lines)


def validate(root, excludes=(), legacy_terms=(), required=DEFAULT_REQUIRED):
    root = Path(root).resolve()
    excludes = tuple(dict.fromkeys(DEFAULT_EXCLUDES + relative_paths(excludes)))
    required = relative_paths(required)
    if any(not term.strip() for term in legacy_terms):
        raise ValueError("Legacy terms must not be empty.")
    errors, warnings = [], []
    checked = private = symlinks = 0
    if not root.is_dir():
        raise ValueError("Vault path is not a directory.")

    for name in required:
        path = root / name
        if not path.is_file() or path.is_symlink():
            errors.append({"file": name, "issue": "required_file_missing_or_symlink"})

    for directory, dirs, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        kept = []
        for name in dirs:
            path = parent / name
            if path.is_symlink():
                symlinks += 1
            elif not name.startswith(".") and not is_excluded(path.relative_to(root), excludes):
                kept.append(name)
        dirs[:] = sorted(kept)
        for name in sorted(files):
            path = parent / name
            relative = path.relative_to(root)
            label = relative.as_posix()
            if path.is_symlink():
                symlinks += 1
                continue
            if name.startswith(".") or path.suffix.lower() != ".md" or is_excluded(relative, excludes):
                continue
            try:
                text = read_nonprivate(path)
            except (OSError, UnicodeError, ValueError):
                errors.append({"file": label, "issue": "unreadable_or_invalid_frontmatter"})
                continue
            if text is None:
                private += 1
                if label in required:
                    errors.append({"file": label, "issue": "required_entry_marked_private"})
                continue
            checked += 1
            if any(term.casefold() in (label + "\n" + text).casefold() for term in legacy_terms):
                errors.append({"file": label, "issue": "legacy_term_requires_review"})
            prose = prose_only(text)
            if re.search(r"\[\[|\]\[[^\]]*\]|(?m:^[ \t]*\[[^\]]+\]:)", prose):
                errors.append({"file": label, "issue": "wiki_or_reference_link_needs_manual_check"})
            for match in LINK.finditer(prose):
                raw = match.group(1).strip("<>")
                try:
                    parsed = urlsplit(raw)
                    if parsed.scheme or parsed.netloc or not parsed.path:
                        continue
                    target = (path.parent / unquote(parsed.path)).resolve()
                    try:
                        target.relative_to(root)
                    except ValueError:
                        warnings.append({"file": label, "issue": "external_local_link_not_checked"})
                        continue
                    if not target.exists():
                        errors.append({"file": label, "issue": "broken_link", "target": raw})
                except (ValueError, OSError):
                    errors.append({"file": label, "issue": "invalid_link"})

    return {
        "status": "FAIL" if errors else "PASS",
        "checked_markdown": checked,
        "private_notes_skipped": private,
        "symlinks_skipped": symlinks,
        "excluded_paths": list(excludes),
        "errors": errors,
        "warnings": warnings,
        "limits": "No private bodies, hidden files, excluded paths or symlinks read; no anchor, remote URL, factual or publication-rights validation.",
    }


def self_test():
    """Temporary fixtures exercise broken links and the private-data boundary."""
    with tempfile.TemporaryDirectory(prefix="personal-ip-vault-check-") as directory:
        root = Path(directory)
        for name in DEFAULT_REQUIRED:
            (root / name).write_text("# Entry\n", encoding="utf-8")
        (root / "a b.md").write_text("# Target\n", encoding="utf-8")
        good = "[angle](<a b.md>)\n[encoded](a%20b.md#heading)\n~~~\n[x](missing-example.md)\n~~~\n"
        (root / "INDEX.md").write_text(good, encoding="utf-8")
        for item in DEFAULT_EXCLUDES:
            folder = root / item
            folder.mkdir(parents=True)
            (folder / "do-not-read.md").write_bytes(b"PRIVATE_FIXTURE\xff")
        (root / "private-note.md").write_bytes(
            b"---\nvisibility: private\n---\nPRIVATE_FIXTURE\xff"
        )
        symlink_test = "passed"
        try:
            (root / "linked-note.md").symlink_to(root / DEFAULT_EXCLUDES[0] / "do-not-read.md")
        except (OSError, NotImplementedError):
            symlink_test = "unavailable_on_this_system"
        report = validate(root, legacy_terms=("PRIVATE_FIXTURE",))
        assert report["status"] == "PASS", report
        assert report["private_notes_skipped"] == 1, report
        if symlink_test == "passed":
            assert report["symlinks_skipped"] == 1, report
        (root / "INDEX.md").write_text("[broken](absent.md)\n", encoding="utf-8")
        assert any(item["issue"] == "broken_link" for item in validate(root)["errors"])
        (root / "INDEX.md").write_text("# OLD_FIXTURE\n", encoding="utf-8")
        assert validate(root, legacy_terms=("old_fixture",))["status"] == "FAIL"
        (root / "INDEX.md").write_text("[[wiki-note]]\n", encoding="utf-8")
        assert validate(root)["status"] == "FAIL"
        try:
            validate(root, excludes=("../outside",))
        except ValueError:
            pass
        else:
            raise AssertionError("An escaping exclude path was accepted.")
    print(json.dumps({"self_test": "PASS", "symlink_test": symlink_test}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", nargs="?")
    parser.add_argument("--exclude", action="append", default=[], metavar="RELATIVE_PATH")
    parser.add_argument("--legacy-term", action="append", default=[], metavar="IDENTIFIER")
    parser.add_argument("--required", action="append", metavar="RELATIVE_FILE")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.vault:
        parser.error("Provide a vault path or --self-test.")
    try:
        report = validate(
            args.vault, args.exclude, args.legacy_term, args.required or DEFAULT_REQUIRED
        )
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
