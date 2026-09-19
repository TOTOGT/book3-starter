#!/usr/bin/env python3
"""Keep the serial from mixing its places again, and keep the typeset copy honest.

Usage:
    python3 continuity_check.py
    python3 continuity_check.py --journal ~/Desktop/AXLE/Journal

Two failures produced this file, and they are different from each other.

1. TOULOUSE AND CASTRES WERE BOTH USED FOR THE DEATH. Part 1 and one line of
   Part 2 put it at Castres, matching the record; another line of Part 2, and
   Part 4 twice, and the whole staging in Part 5 put it at Toulouse. Part 2
   carried both, six lines apart. The record is the load-bearing fact of the
   premise -- Europe wrote down a death at Castres on 12 January 1665 -- so a
   staging in the wrong city makes the record and the fiction describe
   different events.

2. THE JOURNAL'S TYPESET COPY DRIFTED FROM THE SOURCE. The instalments are set
   from the .md files and "never composed at this desk". When the source was
   corrected, the already-published pages in AXLE/Journal still carried the old
   city. A rule that lives only in a note is a rule that holds until somebody
   is in a hurry.

So this script enforces the ruling AND checks that each published instalment is
still the file it was set from.

THE RULING, as of 2026-09-19

  Fermat lives and works in TOULOUSE. Thirty years on the bench of its
  Parlement. He plots there; the carriage leaves from there.

  He dies at CASTRES, on 12 January 1665, two days after signing his last
  judgment -- the chambre de l'edit sat at Castres and he was there on circuit.
  That is the documented record and it is also the plan. Nothing in the serial
  may say he died, or was reported dead, in Toulouse.

  Marie is at VERSAILLES until she leaves. She is never in Toulouse; Toulouse
  is the place she writes to and does not write to.

  Duval is invented and is NOT Medon. Medon's 1653 report was an accident a
  second letter undid. Duval is what it looks like when somebody reads that
  accident as a method.
"""
import argparse
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent

BANNED = [
    (r"die[sd]\s+in\s+Toulouse",      "the death is at Castres, not Toulouse"),
    (r"dead\s+in\s+Toulouse",         "the death is reported from Castres, not Toulouse"),
    (r"death\s+in\s+Toulouse",        "the death is at Castres, not Toulouse"),
    (r"Marie[^.]{0,60}\bin Toulouse", "Marie is at Versailles; she is never in Toulouse"),
    # Only an AFFIRMATIVE merge is a breach. "Duval is not Medon" is the rule
    # itself and is written in several places on purpose; a scanner that flags
    # the statement of a rule as a violation of it commits the defect it exists
    # to catch, which has now happened twice in this corpus's other tools.
    (r"Duval\s+(?:is|was)\s+(?!not\b)[^.]{0,20}\bMedon",
     "Duval is not Medon and the two are never merged"),
    (r"Medon\s*,?\s*(?:also\s+)?(?:known\s+as|called)\s+Duval",
     "Duval is not Medon and the two are never merged"),
]

# Files kept as evidence rather than canon, and working documents that are not
# the book. Both come from build_reader.py's own SKIP set, read at runtime so
# this script cannot disagree with the builder.
#
# The working documents matter for a second reason: FACT_AND_FICTION.md is
# where the rule "Duval is not Medon" is WRITTEN. A scanner that flags the
# statement of a rule as a violation of it is committing the defect it exists
# to catch, which this corpus has now done twice in other tools.
def excluded():
    src = (HERE / "build_reader.py").read_text(encoding="utf-8")
    m = re.search(r"SKIP\s*=\s*\{(.*?)\}", src, re.S)
    names = set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()
    return names | {"README.md", "ISSUE5-PLAN.md", pathlib.Path(__file__).name}


def chapter_order():
    src = (HERE / "build_reader.py").read_text(encoding="utf-8")
    m = re.search(r"CHAPTER_ORDER\s*=\s*\[(.*?)\]", src, re.S)
    if not m:
        raise SystemExit("::error::CHAPTER_ORDER not found in build_reader.py")
    return re.findall(r'"([^"]+\.md)"', m.group(1))


def norm(s):
    """Fold the differences the typesetter is ALLOWED to introduce.

    Three of them, each found by this script flagging a false drift on its
    first run: the .md carries straight quotes and the page carries curly
    ones; the .md marks emphasis with asterisks and the page marks it with a
    tag that the tag-stripper removes; and whitespace differs everywhere. An
    instrument that cannot tell a permitted difference from a forbidden one is
    not usable, and finding that out on its own first run is the cheapest
    place to find it.
    """
    for a, b in [("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2014", "-"), ("\u2013", "-"), ("\u2026", "...")]:
        s = s.replace(a, b)
    s = re.sub(r"[*_]{1,3}", "", s)          # markdown emphasis
    return " ".join(s.split())


def flat_html(p):
    t = p.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    for a, b in [("&#8212;", "—"), ("&#8217;", "’"), ("&#8220;", "“"), ("&#8221;", "”"),
                 ("&#8258;", "‽"), ("&#8230;", "…"), ("&amp;", "&"), ("&#x27;", "'"),
                 ("&quot;", '"'), ("&nbsp;", " "), ("&#183;", "·")]:
        t = t.replace(a, b)
    return " ".join(t.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", default=None)
    a = ap.parse_args()
    if a.journal:
        journal = pathlib.Path(a.journal)
    else:
        # The two trees do not sit at a fixed depth from each other, and an
        # absolute path built from $HOME is wrong under any sandbox. Look.
        journal = None
        for up in list(HERE.parents)[:6]:
            c = up / "AXLE" / "Journal"
            if c.is_dir():
                journal = c
                break
        journal = journal or pathlib.Path("AXLE/Journal")
    fail, note = [], []

    order = chapter_order()
    print("  CHAPTER_ORDER: %d parts" % len(order))

    # --- 1. the ruling, over the canon and over the typeset copies -----------
    skip = excluded()
    targets = [p for p in sorted(HERE.glob("*.md")) if p.name not in skip]
    if journal.is_dir():
        targets += sorted(journal.glob("vol*.html"))
    else:
        note.append("journal folder %s not found; checked the canon only" % journal)

    hits = 0
    for p in targets:
        text = flat_html(p) if p.suffix == ".html" else p.read_text(encoding="utf-8", errors="replace")
        for pat, why in BANNED:
            for m in re.finditer(pat, text, re.I):
                hits += 1
                fail.append("%s: %r -- %s" % (p.name, m.group(0), why))
    print("  ruling checked over %d files; %d violations" % (len(targets), hits))

    # --- 2. each published instalment is still the file it was set from ------
    if journal.is_dir():
        for vp in sorted(journal.glob("vol*.html")):
            t = vp.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"Serial in 18 Parts\s*&#183;\s*Part\s*(\d+)", t)
            if not m:
                continue
            part = int(m.group(1))
            if part > len(order):
                fail.append("%s claims Part %d; CHAPTER_ORDER has %d" % (vp.name, part, len(order)))
                continue
            src = HERE / order[part - 1]
            if not src.exists():
                note.append("%s is Part %d = %s, which is not on this disk"
                            % (vp.name, part, order[part - 1]))
                continue
            if "do not publish this page" in t.lower():
                print("  %-12s Part %-2d  %-34s HELD BACK, not compared"
                      % (vp.name, part, src.name))
                continue
            page = norm(flat_html(vp))
            paras = [norm(q)
                     for q in re.split(r"\n\s*\n", src.read_text(encoding="utf-8"))
                     if q.strip() and not q.lstrip().startswith("#")
                     and set(q.strip()) - set("-*_ ")]
            # Sample first, middle and last. A typeset copy that has been edited
            # at the desk fails on at least one of the three, and a whole-text
            # diff would fail on the masthead and the ledger, which are the
            # page's own and are supposed to differ.
            picks = [0, len(paras) // 2, len(paras) - 1] if len(paras) >= 3 else range(len(paras))
            missing = [k for k in picks if paras[k][:90] not in page]
            print("  %-12s Part %-2d  %-34s %d of %d sampled paragraphs verbatim"
                  % (vp.name, part, src.name, len(picks) - len(missing), len(picks)))
            if missing:
                fail.append("%s has drifted from %s: sampled paragraph(s) %s are not on the "
                            "page verbatim. The instalment is set from the file and is never "
                            "composed at the desk." % (vp.name, src.name, missing))

    print()
    for n in note:
        print("  NOTE  " + n)
    for f in fail:
        print("::error::" + f)
    if fail:
        return 1
    print("the ruling holds, and every published instalment still matches its source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
