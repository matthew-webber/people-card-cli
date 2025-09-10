#!/usr/bin/env python3
"""
Find matches in the latest pct-*.xlsx based on names in names.txt.

- Chooses the pct-*.xlsx with the highest numeric suffix (e.g., pct-0910.xlsx > pct-0901.xlsx).
- Reads names.txt; if a line contains credentials after the first comma, strips them.
- Overwrites names.txt with the stripped names (one per line, preserving order).
- For each stripped name, searches Column A of the Excel file for an exact match of:
      lastname[-middle_initial]-firstname
  where the middle initial (single letter) is optional.
- Prints matches with row numbers (1-indexed as in Excel).
"""

import glob
import os
import re
import sys
from typing import List, Tuple, Optional
import pyperclip
import json

try:
    import pandas as pd
except ImportError:
    print(
        "This script requires pandas. Install with: pip install pandas", file=sys.stderr
    )
    sys.exit(1)


PCT_PREFIX = "pct-"
PCT_PATTERN = re.compile(r"^pct-(\d+)\.xlsx$", re.IGNORECASE)
NAMES_FILE = "names.txt"


def pick_latest_pct_xlsx() -> str:
    candidates = []
    for path in glob.glob(f"{PCT_PREFIX}*.xlsx"):
        fname = os.path.basename(path)
        m = PCT_PATTERN.match(fname)
        if m:
            try:
                num = int(m.group(1))
                candidates.append((num, path))
            except ValueError:
                continue
    if not candidates:
        raise FileNotFoundError("No pct-*.xlsx files found in current directory.")
    # Max by numeric suffix
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]


def load_and_strip_names(path: str) -> List[str]:
    """
    Read names.txt. If a comma exists, everything after the FIRST comma is treated
    as credentials and removed. Returns stripped names (non-empty).
    Also overwrites the file with the stripped names.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found.")
    stripped: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            # Split at the FIRST comma; right part (if any) are credentials to drop
            name_only = raw.split(",", 1)[0].strip()
            if name_only:
                stripped.append(name_only)

    # Overwrite names.txt with stripped names
    with open(path, "w", encoding="utf-8") as f:
        for name in stripped:
            f.write(name + "\n")

    return stripped


def tokenize_name(name: str) -> Tuple[str, Optional[str], str]:
    """
    Parse a loose human name into (first, middle_initial_optional, last).
    Assumptions:
      - Input like "First M Last" OR "First Middle Last" OR "First Last"
      - We also try to handle "Last First Middle" if user wrote last-first order with hyphens/spaces,
        but since credentials are already stripped at the first comma, commas are not used inside names.
    Rules:
      - The LAST token is treated as last name.
      - The FIRST token is first name.
      - Anything in between contributes a middle initial: first letter of the first middle token.
      - Tokens consisting of a single letter (with/without period) are treated as middle initials.
    """
    # Remove stray punctuation that’s not helpful for name parsing
    cleaned = re.sub(
        r"[^\w\s\-\.']", " ", name
    )  # allow letters/digits, whitespace, hyphen, dot, apostrophe
    parts = [p for p in re.split(r"\s+", cleaned.strip()) if p]
    if len(parts) < 2:
        # If we can't parse, fall back to using the whole thing as first name
        return (parts[0], None, "") if parts else ("", None, "")

    first = parts[0]
    last = parts[-1]
    middle_tokens = parts[1:-1]

    mid_initial = None
    if middle_tokens:
        # Prefer the first token; if it's like "M." or "M", take 'M'. If it's a name, take its first letter.
        mt = middle_tokens[0].strip(".")
        if mt:
            mid_initial = mt[0]

    return first, mid_initial, last


def key_variants_from_name(name: str) -> List[str]:
    """
    Build candidate keys to match column A:
        lastname-firstname
        lastname-M-firstname  (if middle initial is available)
    Normalize to lowercase; keep hyphens and apostrophes inside names.
    """
    first, mid, last = tokenize_name(name)

    # Normalize name components: lowercase, collapse multiple hyphens/spaces inside, remove periods
    def norm(s: str) -> str:
        s = s.replace(".", "")
        s = re.sub(r"\s+", " ", s.strip().lower())
        return s

    first_n = norm(first)
    last_n = norm(last)

    variants = []
    if last_n and first_n:
        variants.append(f"{last_n}-{first_n}")

    if mid:
        mid_n = norm(mid)[0] if norm(mid) else ""
        if mid_n:
            variants.append(f"{last_n}-{mid_n}-{first_n}")

    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for v in variants:
        if v not in seen:
            uniq.append(v)
            seen.add(v)
    return uniq


def load_column_a_as_keys(xlsx_path: str) -> pd.Series:
    """
    Load Column A as normalized lowercase strings for exact-equality matching.
    Rows that are NaN/empty are dropped from the internal index, but we keep
    the original Excel row number separately when reporting.
    """
    df = pd.read_excel(
        xlsx_path, header=None, dtype=str, engine="openpyxl"
    )  # no header
    if df.shape[1] < 1:
        raise ValueError("Excel file has no columns.")
    colA = df.iloc[:, 0].fillna("").astype(str)

    # Normalize similarly to the generated keys (lowercase, strip spaces, remove surrounding spaces)
    def normalize_cell(s: str) -> str:
        s = s.replace(".", "")
        s = re.sub(r"\s+", " ", s.strip().lower())
        return s

    normalized = colA.apply(normalize_cell)
    return normalized


def main():
    try:
        xlsx_path = pick_latest_pct_xlsx()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        names = load_and_strip_names(NAMES_FILE)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(3)

    try:
        colA_norm = load_column_a_as_keys(xlsx_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(4)

    print(f"Using Excel: {os.path.basename(xlsx_path)}")
    print(
        f"Loaded {len(names)} name(s) from {NAMES_FILE} (credentials stripped if present)."
    )
    print()

    # Build a reverse index: normalized value -> list of row numbers (1-indexed like Excel)
    value_to_rows = {}
    for idx, val in colA_norm.items():
        if not val:
            continue
        # Excel rows are 1-indexed; plus headerless dataframe, so row 0 is Excel row 1
        excel_row = idx + 1
        value_to_rows.setdefault(val, []).append(excel_row)

    total_found = 0
    for name in names:
        variants = key_variants_from_name(name)
        found_rows = []
        for v in variants:
            if v in value_to_rows:
                found_rows.extend(value_to_rows[v])

        # Dedup and sort row numbers
        found_rows = sorted(set(found_rows))
        key_display = " OR ".join(variants) if variants else "(unparsable)"
        if found_rows:
            total_found += 1
            print(f"[MATCH] {name} -> {key_display}  |  Rows: {found_rows}")
        else:
            print(f"[MISS ] {name} -> {key_display}")

    print()
    print(f"Done. {total_found}/{len(names)} had at least one match in Column A.")

    return names


def card_finder_js(names: List[str]) -> str:
    js_template = r"""
// JavaScript snippet to find a person card by name on a webpage
(async () => {{
  // --- DEBUG SETUP ---
  myDebug = 3;
  myDebugLevels = {{
    DEBUG: 1,
    INFO: 2,
    WARN: 3,
  }};

  // --- INPUT: person full name as "first_name last_name" ---
  // Prompt for name, remembering last entry in localStorage
  // const lastPerson = localStorage.getItem('lastPersonName') || 'John Smith';
  // const personName = prompt("Enter person's name (first last):", lastPerson);

  // Check if names were provided from Python script
  const providedNames = {names};

  if (!providedNames.length > 0) {{
    console.error('No names provided from Python script.');
    return;
  }}

  const peopleCardData = providedNames.map((name) => ({{
    name,
    found: false,
    headshotImgString: null,
  }}));

  // --- Helpers ---
  const sanitizeName = (name) =>
    String(name || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/\p{{Diacritic}}/gu, '')
      .replace(/[-_]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

  const canonicalKebab = (s) =>
    String(s || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/\p{{Diacritic}}/gu, '')
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');

  function parsePersonName(full) {{
    const s = sanitizeName(full);
    const parts = s.split(' ');
    if (parts.length < 2) {{
      throw new Error('Expected "first last" but got: ' + full);
    }}
    const first = parts[0];
    const last = parts.slice(1).join(' ');
    return {{ first, last }};
  }}

  async function countdown(seconds) {{
    // if seconds === 0, wait until window.userReady === true
    if (seconds === 0) {{
      window.userReady = false;
      let num_waits = 0;
      console.log('Waiting for userReady to be true...');
      while (!window.userReady && num_waits < 12) {{
        console.log('Waiting...');
        await new Promise((resolve) => setTimeout(resolve, 5000));
        num_waits++;
      }}
      console.log('userReady is now true.');
      return;
    }}
    for (let i = seconds; i > 0; i--) {{
      console.log(`Moving to next provider in ${{i}}...`);
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }}
  }}

  const BASE_PATH = [
    'Redesign Data',
    'Modules Global Data',
    'People Cards',
    'People Card Data',
  ];

  function computeLetterAndRange(last) {{
    const clean = canonicalKebab(last).replace(/-/g, '');
    const firstLetter = (clean[0] || '').toUpperCase();
    if (!firstLetter || !/[A-Z]/.test(firstLetter)) {{
      throw new Error('Last name must start with A-Z: ' + last);
    }}
    const secondLetter = (clean[1] || 'a').toLowerCase();
    let bucketStart, bucketEnd;
    if (secondLetter >= 'a' && secondLetter <= 'i') {{
      bucketStart = 'a';
      bucketEnd = 'i';
    }} else if (secondLetter >= 'j' && secondLetter <= 'r') {{
      bucketStart = 'j';
      bucketEnd = 'r';
    }} else {{
      bucketStart = 's';
      bucketEnd = 'z';
    }}
    const letterFolder = firstLetter; // e.g. "S"
    const rangeFolder = `${{firstLetter}}${{bucketStart}}-${{firstLetter}}${{bucketEnd}}`; // e.g. "Sj-Sr"
    return {{ letterFolder, rangeFolder }};
  }}

  function buildExactRegex(last, first) {{
    const lastK = canonicalKebab(last);
    const firstK = canonicalKebab(first);
    const pattern = `^${{lastK}}-${{firstK}}-\\d{{4}}$`;
    if (myDebug < myDebugLevels.WARN) console.log('Exact regex:', pattern);
    return new RegExp(pattern, 'i');
  }}

  function buildLastPlusFirstInitialRegex(last, first) {{
    const lastK = canonicalKebab(last);
    const firstInitial = canonicalKebab(first).charAt(0) || '';
    // allow hyphens in first-name remainder, keep required 4 digits at end
    const pattern = `^${{lastK}}-${{firstInitial}}[a-z0-9-]*-\\d{{4}}$`;
    if (myDebug < myDebugLevels.WARN)
      console.log('Last+FirstInitial regex:', pattern);
    return new RegExp(pattern, 'i');
  }}

  function buildLastOnlyRegex(last) {{
    const lastK = canonicalKebab(last);
    const pattern = `^${{lastK}}-[a-z0-9-]+-\\d{{4}}$`;
    if (myDebug < myDebugLevels.WARN) console.log('Last-only regex:', pattern);
    return new RegExp(pattern, 'i');
  }}

  function buildFirstLetterRegex(last) {{
    const letter = (canonicalKebab(last)[0] || '').toLowerCase();
    const pattern = `^${{letter}}[a-z0-9-]*-\\d{{4}}$`;
    if (myDebug < myDebugLevels.WARN)
      console.log('First-letter regex:', pattern);
    return new RegExp(pattern, 'i');
  }}

  // --- Tree search utils ---
  const findNodeExact = (name, searchRoot = document) =>
    Array.from(searchRoot.querySelectorAll('.scContentTreeNode')).find(
      (node) => {{
        const target = sanitizeName(name);
        const span = node.querySelector('span');
        if (!span) {{
          console.warn('no span for', name);
          return false;
        }}
        if (myDebug < myDebugLevels.INFO) {{
          console.log('span', span, 'textContent', span.textContent);
          console.log(
            'SANITIZED span.textContent:',
            sanitizeName(span.textContent),
            'target:',
            target
          );
          console.log(
            'checking "sanitizeName(span.textContent) === target":',
            sanitizeName(span.textContent),
            '===',
            target
          );
        }}
        return span && sanitizeName(span.textContent) === target;
      }}
    );

  function waitForMatchExact(name, searchRoot = document, timeout = 5000) {{
    return new Promise((resolve, reject) => {{
      const start = Date.now();
      (function check() {{
        const m = findNodeExact(name, searchRoot);
        if (m) return resolve(m);
        if (Date.now() - start > timeout)
          return reject(new Error('Timeout waiting for ' + name));
        setTimeout(check, 500);
      }})();
    }});
  }}

  async function expand(name, searchRoot = document) {{
    const node = await waitForMatchExact(name, searchRoot);
    const arrow = node.querySelector('img');
    if (!arrow) {{
      console.warn('no expand arrow for', name);
      return node;
    }}
    if (myDebug < myDebugLevels.WARN) {{
      console.log('expanding', name, 'found node:', node, 'with arrow:', arrow);
    }}
    if (node.lastElementChild && node.lastElementChild.tagName === 'DIV') {{
      console.log('already expanded', name);
      return node;
    }}
    arrow.click();
    await new Promise((r) => setTimeout(r, 250));
    return node;
  }}

  function findNodesByRegex(regex, searchRoot = document) {{
    const nodes = Array.from(
      searchRoot.querySelectorAll('.scContentTreeNode')
    ).filter((node) => {{
      const span = node.querySelector('span');
      if (!span) return false;
      const txt = (span.textContent || '').trim();
      const ok = regex.test(txt);
      if (myDebug < myDebugLevels.INFO) {{
        console.log('Testing node text:', txt, 'against', regex, '=>', ok);
      }}
      return ok;
    }});
    return nodes;
  }}

  function waitForRegex(regex, searchRoot = document, timeout = 5000) {{
    return new Promise((resolve, reject) => {{
      const start = Date.now();
      (function check() {{
        const matches = findNodesByRegex(regex, searchRoot);
        if (matches.length) return resolve(matches);
        if (Date.now() - start > timeout)
          return reject(new Error('Timeout waiting for regex: ' + regex));
        setTimeout(check, 500);
      }})();
    }});
  }}

  async function clickFirstRegex(regex, searchRoot = document, timeout = 2500) {{
    const matches = await waitForRegex(regex, searchRoot, timeout);
    const node = matches[0];
    const span = node.querySelector('span');
    if (span) {{
      if (myDebug < myDebugLevels.WARN) {{
        console.log('Clicking node:', span.textContent);
      }}
      span.click();
      await countdown(1);
      console.log('Out of clickFirstRegex 💰💰💰💰💰');
      return true;
    }} else {{
      console.warn('no span to click for regex match');
      return false;
    }}
  }}

  function getHeadshotImageString(searchRoot = document) {{
    // Find the span whose text contains "Headshot Image" (non-strict match)
    const targetSpan = Array.from(searchRoot.querySelectorAll('span')).find(
      (span) => (span.textContent || '').includes('Headshot Image')
    );

    let val;

    if (targetSpan) {{
      // Step 1: get the parent of that span
      const parent = targetSpan.parentElement;
      // Step 2: get the next sibling element
      const sibling = parent?.nextElementSibling;
      // Step 3: find the input inside that sibling
      const input = sibling?.querySelector('input');
      // Step 4: get the value attribute
      val = input?.getAttribute('value');
    }} else {{
      console.warn("No span containing 'Headshot Image' found.");
    }}
    return val;
  }}

  for (const person of peopleCardData) {{
    try {{
      // 1) Parse, compute path
      const {{ first, last }} = parsePersonName(person.name);
      const {{ letterFolder, rangeFolder }} = computeLetterAndRange(last);
      const expandNames = [...BASE_PATH, letterFolder, rangeFolder];

      // 2) Expand down to the range folder
      let currentSearchRoot = document;
      for (const name of expandNames) {{
        const expandedNode = await expand(name, currentSearchRoot);
        currentSearchRoot = expandedNode; // scope subsequent searches
      }}

      // 3) Try exact, then fallbacks
      const exactRe = buildExactRegex(last, first);
      const lastPlusInitialRe = buildLastPlusFirstInitialRegex(last, first);
      const lastOnlyRe = buildLastOnlyRegex(last);
      const firstLetterRe = buildFirstLetterRegex(last);

      // exact
      try {{
        if (await clickFirstRegex(exactRe, currentSearchRoot, 3000)) {{
          person.found = true;
          c = getHeadshotImageString();
          person.headshotImgString = c;
          continue;
        }}
      }} catch (e) {{
        if (myDebug < myDebugLevels.WARN)
          console.log('Exact match timed out, trying fallbacks...', e.message);
      }}

      // last + first initial
      try {{
        if (await clickFirstRegex(lastPlusInitialRe, currentSearchRoot, 2000))
          continue;
      }} catch (e) {{
        if (myDebug < myDebugLevels.WARN)
          console.log(
            'Last+FirstInitial timed out, next fallback...',
            e.message
          );
      }}

      // last name only
      try {{
        if (await clickFirstRegex(lastOnlyRe, currentSearchRoot, 2000))
          continue;
      }} catch (e) {{
        if (myDebug < myDebugLevels.WARN)
          console.log('Last-only timed out, final fallback...', e.message);
      }}

      // first letter (this should always exist within the range)
      try {{
        if (await clickFirstRegex(firstLetterRe, currentSearchRoot, 2000))
          continue;
      }} catch (e) {{
        console.warn(
          'First-letter fallback timed out; nothing clickable matched expected patterns.'
        );
      }}
    }} catch (e) {{
      console.error(e);
    }}
  }}
  console.log('People card data results:', peopleCardData);
  return peopleCardData;
}})();

"""
    return js_template.format(names=json.dumps(names))


if __name__ == "__main__":
    names = main()
    print(f"Names to search for: {names}!!!!!!!!\n")

    js = card_finder_js(names)  # generate JS snippet

    # send JS to clipboard if possible
    try:

        pyperclip.copy(js)
        print()
        print("JavaScript snippet copied to clipboard.")
    except ImportError:
        print()
        print("Install pyperclip to enable clipboard copy: pip install pyperclip")
        print("Here is the JavaScript snippet:")
        print()
        print(js)
