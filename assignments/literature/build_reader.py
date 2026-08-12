#!/usr/bin/env python3
"""
build_reader.py — assembles the literature chapters into a single paginated,
printable HTML reader.

Run it from inside assignments/literature/:

    python3 build_reader.py

Writes reader.html. Open in a browser, click PRINT — the page is numbered,
capped at MAX_PAGES, and closes on "To be continued…".

Chapters are emitted in CHAPTER_ORDER. Any .md in the folder that is not
listed and not in SKIP is appended at the end with a warning, so nothing
silently goes missing.
"""

import os, re, html, json, sys

MAX_PAGES = 50

# Canon order. Files absent from disk are skipped silently — so this same
# script works here (my chapters only) and in TOTOGT/book3-starter (all of them).
CHAPTER_ORDER = [
    "fermat_opening.md",
    "fermat_commission.md",
    "the_unfinished_cage.md",
    "marie_flight.md",
    "what_the_plague_made_easy.md",
    "the_boy_who_carried_nothing.md",
    "the_clerk_who_never_bathed.md",
    "what_the_sea_already_knew.md",
    "the_small_colorful_demons.md",
    "what_the_cat_wanted.md",
    "the_ceiling.md",
    "what_the_name_was_still_doing_there.md",
    "we_built_it_last_week.md",
    "the_children_of_the_sea.md",
    "o_conselheiro.md",
    "what_the_margin_was_for.md",
    "what_arrived_without_its_head.md",
    "what_he_had_no_idea_he_had_done.md",
]

# Working documents — not part of the book.
SKIP = {
    "FACT_AND_FICTION.md",
    "RECONCILIATION.md",
    "Fermat.md",
    "what_the_shore_was_called.md",          # superseded
    "the_man_who_could_not_be_interesting.md",  # superseded: Jews stay off the page
    "the_small_colorful_demons (1).md",
    "what_the_plague_made_easy (1).md",
}


def md_to_blocks(text):
    """Very small markdown subset -> list of html blocks."""
    lines = text.split("\n")
    title, subtitle, body = None, None, []
    i = 0
    # H1 = chapter title
    while i < len(lines):
        if lines[i].startswith("# "):
            title = lines[i][2:].strip()
            i += 1
            break
        i += 1
    # first non-empty, non-rule line after the title = the place/time line
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith("*(") or s.startswith("---"):
            i += 1
            continue
        if not s.startswith("#"):
            subtitle = s.strip("*")
            i += 1
        break

    buf = []
    for line in lines[i:]:
        s = line.rstrip()
        if s.strip() == "---":
            if buf:
                body.append(("p", " ".join(buf)));  buf = []
            body.append(("hr", ""))
        elif not s.strip():
            if buf:
                body.append(("p", " ".join(buf)));  buf = []
        elif s.startswith("### "):
            if buf:
                body.append(("p", " ".join(buf)));  buf = []
            body.append(("h3", s[4:].strip()))
        elif s.startswith("## "):
            if buf:
                body.append(("p", " ".join(buf)));  buf = []
            body.append(("h3", s[3:].strip()))
        elif s.startswith("> "):
            if buf:
                body.append(("p", " ".join(buf)));  buf = []
            body.append(("bq", s[2:].strip()))
        else:
            buf.append(s.strip())
    if buf:
        body.append(("p", " ".join(buf)))
    return title, subtitle, body


def inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", t)   # strip links for print
    return t


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    present = {f for f in os.listdir(here) if f.endswith(".md")}
    ordered = [f for f in CHAPTER_ORDER if f in present]
    leftovers = sorted(present - set(CHAPTER_ORDER) - SKIP)
    if leftovers:
        print("  ! not in CHAPTER_ORDER, appending at end:", ", ".join(leftovers))
    ordered += leftovers

    if not ordered:
        sys.exit("No chapter .md files found in this folder.")

    chapters = []
    for fn in ordered:
        with open(os.path.join(here, fn), encoding="utf-8") as fh:
            raw = fh.read()
        title, subtitle, body = md_to_blocks(raw)
        if not title:
            continue
        parts = []
        for kind, txt in body:
            if kind == "hr":
                parts.append('<div class="brk">&#10022;</div>')
            elif kind == "h3":
                parts.append(f"<h3>{inline(txt)}</h3>")
            elif kind == "bq":
                parts.append(f"<blockquote>{inline(txt)}</blockquote>")
            else:
                parts.append(f"<p>{inline(txt)}</p>")
        chapters.append({
            "title": title,
            "sub": subtitle or "",
            "html": "".join(parts),
        })
        print(f"  + {fn}")

    words = sum(len(re.sub("<[^>]+>", " ", c["html"]).split()) for c in chapters)
    print(f"\n  {len(chapters)} chapters, ~{words:,} words "
          f"(~{words // 380} pages at 380 w/p; capped at {MAX_PAGES})")

    out = TEMPLATE.replace("__DATA__", json.dumps(chapters, ensure_ascii=False)) \
                  .replace("__MAXPAGES__", str(MAX_PAGES))
    dest = os.path.join(here, "reader.html")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"  -> {dest}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pierre et Mademoiselle — Reader</title>
<style>
:root{--navy:#1a2744;--gold:#c9a84c;--cream:#faf7f0;--ink:#16161a;--mute:#6a6a72;--rule:#d8d2c4}
*{box-sizing:border-box}
body{margin:0;background:#e8e4da;font:16px/1.6 Georgia,'Times New Roman',serif;color:var(--ink)}
#bar{position:sticky;top:0;z-index:50;background:var(--navy);color:var(--cream);
  padding:12px 20px;display:flex;gap:14px;align-items:center;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;font-size:13px}
#bar b{letter-spacing:.14em;text-transform:uppercase;font-size:11px;color:var(--gold)}
#bar .sp{flex:1}
button{background:var(--gold);color:#16161a;border:0;padding:9px 20px;border-radius:2px;
  font:600 12px/1 -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
  letter-spacing:.1em;text-transform:uppercase;cursor:pointer}
button:hover{filter:brightness(1.08)}
#count{color:#a9a9a2;font-size:12px}
#book{padding:26px 0}
.page{width:816px;height:1056px;margin:0 auto 22px;background:var(--cream);
  padding:96px 96px 72px;position:relative;box-shadow:0 2px 14px rgba(0,0,0,.16);overflow:hidden}
.folio{position:absolute;left:96px;right:96px;bottom:38px;text-align:center;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
  font-size:10.5px;letter-spacing:.22em;color:var(--mute)}
.rh{position:absolute;left:96px;right:96px;top:52px;display:flex;justify-content:space-between;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
  font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:#9a978e;
  border-bottom:1px solid var(--rule);padding-bottom:6px}
h2.ct{font-size:30px;font-weight:400;line-height:1.15;margin:0 0 4px;color:var(--navy)}
.cs{font-style:italic;color:var(--mute);font-size:14.5px;margin-bottom:22px;
  padding-bottom:14px;border-bottom:1px solid var(--rule)}
h3{font-size:17px;font-weight:400;color:var(--navy);margin:18px 0 6px}
p{margin:0 0 12px;text-align:justify;hyphens:auto}
blockquote{margin:12px 24px;font-style:italic;color:#3a3a40}
code{font-family:ui-monospace,Menlo,monospace;font-size:.86em}
.brk{text-align:center;color:var(--gold);margin:16px 0;font-size:13px;letter-spacing:.5em}
/* title page */
.tp{display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;height:100%}
.tp .ey{font-family:-apple-system,sans-serif;font-size:10.5px;letter-spacing:.3em;
  text-transform:uppercase;color:var(--gold);margin-bottom:26px}
.tp h1{font-size:52px;font-weight:400;margin:0;line-height:1.05;color:var(--navy)}
.tp h1 em{color:var(--gold)}
.tp .rule{width:78px;height:2px;background:var(--gold);margin:24px 0}
.tp .dk{font-style:italic;color:#4a4a52;max-width:430px;font-size:16px}
.tp .by{margin-top:44px;font-family:-apple-system,sans-serif;font-size:11.5px;
  letter-spacing:.13em;color:var(--mute);line-height:2}
/* end page */
.tbc{display:flex;flex-direction:column;justify-content:center;align-items:center;height:100%;text-align:center}
.tbc .big{font-size:30px;font-style:italic;color:var(--navy)}
.tbc .sm{margin-top:20px;font-family:-apple-system,sans-serif;font-size:11px;
  letter-spacing:.2em;text-transform:uppercase;color:var(--mute)}
@media print{
  @page{size:letter;margin:0}
  body{background:#fff}
  #bar{display:none}
  #book{padding:0}
  .page{margin:0;box-shadow:none;break-after:page;page-break-after:always}
  .page:last-child{break-after:auto;page-break-after:auto}
}
</style></head><body>

<div id="bar">
  <b>Pierre et Mademoiselle</b>
  <span id="count">paginating…</span>
  <span class="sp"></span>
  <button onclick="window.print()">Print / Save PDF</button>
</div>

<div id="book"></div>

<script>
const CHAPTERS = __DATA__;
const MAXPAGES = __MAXPAGES__;
const RUNHEAD  = "Pierre et Mademoiselle";

const book = document.getElementById('book');

function newPage(){
  const p = document.createElement('div');
  p.className = 'page';
  book.appendChild(p);
  return p;
}
function frame(page, right, n){
  const rh = document.createElement('div');
  rh.className = 'rh';
  rh.innerHTML = '<span>'+RUNHEAD+'</span><span>'+right+'</span>';
  page.insertBefore(rh, page.firstChild);
  const f = document.createElement('div');
  f.className = 'folio';
  f.textContent = n;
  page.appendChild(f);
}

/* --- title page --- */
const tp = newPage();
tp.innerHTML = '<div class="tp">'+
  '<div class="ey">A Limited Series &middot; Sample Pages</div>'+
  '<h1>Pierre <em>et</em> Mademoiselle</h1>'+
  '<div class="rule"></div>'+
  '<div class="dk">In 1665 the greatest mathematician in Europe proved that a man could stop existing. '+
  'It was the only theorem he ever tested on himself.</div>'+
  '<div class="by">Pablo Nogueira Grossi<br>G6 LLC &middot; Newark, New Jersey<br>'+
  'Based on the true and documented death of Pierre de Fermat</div></div>';

/* --- flow the chapters --- */
let pageNo = 0, page = null, body = null, done = false;

function startPage(runRight){
  page = newPage();
  pageNo++;
  frame(page, runRight, pageNo);
  body = document.createElement('div');
  page.appendChild(body);
}
function fits(){
  // 1056 height - 96 top pad - 72 bottom pad, minus runhead/folio allowance
  return body.getBoundingClientRect().height <= 806;
}

outer:
for (const ch of CHAPTERS){
  startPage(ch.title);
  const head = document.createElement('div');
  head.innerHTML = '<h2 class="ct">'+ch.title+'</h2>'+
                   (ch.sub ? '<div class="cs">'+ch.sub+'</div>' : '');
  body.appendChild(head);

  const tmp = document.createElement('div');
  tmp.innerHTML = ch.html;
  const blocks = Array.from(tmp.children);

  for (const b of blocks){
    body.appendChild(b);
    if (!fits()){
      body.removeChild(b);
      if (pageNo >= MAXPAGES){ done = true; break outer; }
      startPage(ch.title);
      body.appendChild(b);
    }
  }
  if (pageNo >= MAXPAGES){ done = true; break; }
}

/* --- to be continued --- */
const end = newPage();
end.innerHTML = '<div class="tbc"><div class="big">To be continued&hellip;</div>'+
  '<div class="sm">Sample ends at page '+pageNo+'</div></div>';

document.getElementById('count').textContent =
  pageNo + ' numbered pages' + (done ? ' · capped at ' + MAXPAGES : '');
</script>
</body></html>
"""

if __name__ == "__main__":
    main()
