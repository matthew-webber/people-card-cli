"""
Scan pct-*.xlsx for name matches and generate a JS snippet.

This command replicates the functionality of the previous standalone script
by searching the latest pct-*.xlsx for exact name keys and reporting matches.
It also generates a Sitecore helper JavaScript snippet and copies it to the
clipboard when possible.
"""

from __future__ import annotations

import glob
import os
import re
import sys
from typing import List, Tuple, Optional
import json

try:
    import pandas as pd
except ImportError:
    print(
        "This command requires pandas. Install with: pip install pandas",
        file=sys.stderr,
    )
    raise


PCT_PREFIX = "pct-"
PCT_PATTERN = re.compile(r"^pct-(\d+)\.xlsx$", re.IGNORECASE)
NAMES_FILE = "names.txt"


def _pick_latest_pct_xlsx() -> str:
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
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]


def _load_and_strip_names(path: str) -> List[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found.")
    stripped: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            name_only = raw.split(",", 1)[0].strip()
            if name_only:
                stripped.append(name_only)

    with open(path, "w", encoding="utf-8") as f:
        for name in stripped:
            f.write(name + "\n")

    return stripped


def _tokenize_name(name: str) -> Tuple[str, Optional[str], str]:
    quote_replaced_name = name.replace("“", '"').replace("”", '"')
    cleaned = re.sub(r"""[^"\w\s\-\.' ]""", " ", quote_replaced_name)
    cleaned = re.sub(
        r"\b(Jr|Sr|II|III|IV|V|MD|PhD|Esq)\.?\s*$", "", cleaned, flags=re.IGNORECASE
    )
    parts = [p for p in re.split(r"\s+", cleaned.strip()) if p]
    if len(parts) < 2:
        return (parts[0], None, "") if parts else ("", None, "")

    for p in parts:
        if '"' in p:
            match = re.search(r'"(.*?)"', p)
            if match:
                first = match.group(1)
                break
        if re.match(r"^[A-Za-z]\.?$", parts[0]):
            first = parts[1] if len(parts) > 1 else parts[0]
            break
    else:
        first = parts[0]

    last = parts[-1]
    middle_tokens = parts[1:-1]

    mid_initial = None
    if middle_tokens:
        mt = middle_tokens[0].strip(".")
        if mt:
            mid_initial = mt[0]

    return first, mid_initial, last


def _key_variants_from_name(name: str) -> List[str]:
    first, mid, last = _tokenize_name(name)

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

    seen = set()
    uniq = []
    for v in variants:
        if v not in seen:
            uniq.append(v)
            seen.add(v)
    return uniq


def _load_column_a_as_keys(xlsx_path: str) -> pd.Series:
    df = pd.read_excel(xlsx_path, header=None, dtype=str, engine="openpyxl")
    if df.shape[1] < 1:
        raise ValueError("Excel file has no columns.")
    colA = df.iloc[:, 0].fillna("").astype(str)

    def normalize_cell(s: str) -> str:
        # remove periods
        s = s.replace(".", "")
        # normalize whitespace, lowercase
        s = re.sub(r"\s+", " ", s.strip().lower())
        # remove -#### suffixes
        s = re.sub(r"-\d{4}$", "", s)
        return s

    return colA.apply(normalize_cell)


def _card_finder_js(names: List[Tuple[str, str]]) -> str:
    js_template = r"""
// JavaScript snippet to find a person card by name on a webpage
(async () => {{
  // --- DEBUG SETUP ---
  myDebug = 1;
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
    // if seconds === 0, wait until window.pFound === true
    if (seconds === 0) {{
      window.pFound = null;
      let num_waits = 0;
      console.log('Waiting (up to 30s) for window.pFound to be true...');
      console.log('***DIRECTIONS***');
      console.log('1. Set window.pFound = true in the console to grab the headshot string.');
      console.log('2. If person not found, set window.pFound = false to skip.');
      console.log('3. If nothing happens after 30s, the script will continue automatically.');
      while (window.pFound === null && num_waits < 10) {{
        console.log('Waiting...');
        await new Promise((resolve) => setTimeout(resolve, 3000));
        num_waits++;
      }}
      console.log('pFound is now true.');
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
    if (myDebug < myDebugLevels.INFO) console.log('Exact regex:', pattern);
    return new RegExp(pattern, 'i');
  }}

  function buildLastPlusFirstInitialRegex(last, first) {{
    const lastK = canonicalKebab(last);
    const firstInitial = canonicalKebab(first).charAt(0) || '';
    // allow hyphens in first-name remainder, keep required 4 digits at end
    const pattern = `^${{lastK}}-${{firstInitial}}[a-z0-9-]*-\\d{{4}}$`;
    if (myDebug < myDebugLevels.INFO)
      console.log('Last+FirstInitial regex:', pattern);
    return new RegExp(pattern, 'i');
  }}

  function buildLastOnlyRegex(last) {{
    const lastK = canonicalKebab(last);
    const pattern = `^${{lastK}}-[a-z0-9-]+-\\d{{4}}$`;
    if (myDebug < myDebugLevels.INFO) console.log('Last-only regex:', pattern);
    return new RegExp(pattern, 'i');
  }}

  function buildFirstLetterRegex(last) {{
    const letter = (canonicalKebab(last)[0] || '').toLowerCase();
    const pattern = `^${{letter}}[a-z0-9-]*-\\d{{4}}$`;
    if (myDebug < myDebugLevels.INFO)
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
    if (myDebug < myDebugLevels.INFO) {{
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
        // console.log('Testing node text:', txt, 'against', regex, '=>', ok);
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

  async function clickFirstRegex(scope, regex, searchRoot = document, timeout = 2500) {{
    const matches = await waitForRegex(regex, searchRoot, timeout);
    const node = matches[0];
    const span = node.querySelector('span');
    if (span) {{
      if (myDebug < myDebugLevels.WARN) {{
        console.log('Clicking node:', span.textContent);
      }}
      span.click();
      if (scope !== 'exact') {{console.log('scope is', scope); await countdown(0);}}
      return true;
    }} else {{
      console.warn('no span to click for regex match');
      return false;
    }}
  }}

  async function getHeadshotImageString(searchRoot = document) {{
    let val = null;
    // Step 0: pause briefly to allow UI to update
    console.log('🐢 Waiting 1.5s for UI to update...');
    await new Promise((r) => setTimeout(r, 1500));
    // Find the span whose text contains "Headshot Image" (non-strict match)
    const targetSpan = Array.from(searchRoot.querySelectorAll('span')).find(
      (span) => (span.textContent || '').includes('Headshot Image')
    );

    if (targetSpan) {{
      // Step 1: get the parent of that span
      const parent = targetSpan.parentElement;
      // Step 2: get the next sibling element
      const sibling = parent?.nextElementSibling;
      // Step 3: find the input inside that sibling
      const input = sibling?.querySelector('input');
      // Step 4: get the value attribute
      const val = input?.getAttribute('value');
    }} else {{
      console.warn("No span containing 'Headshot Image' found.");
    }}
    return val || null;
  }}

  const conditionallyModifyPeopleCardData = async () => {{
    if (window.pFound === true) {{
        person.found = true;
        person.headshotImgString = await getHeadshotImageString(currentSearchRoot);
      }} else {{
        console.log('Skipping headshot grab as pFound is not true.');
      }}
    }};

  for (const person of peopleCardData) {{
    try {{
      // 1) Parse, compute path
      const [first, last] = person.name;
      if (myDebug < myDebugLevels.WARN) console.log(`Searching for: ${{person.name}} => first: ${{first}}, last: ${{last}}`);
      if (!first || !last) {{
        console.warn('Skipping unparsable name:', person.name);
        continue;
      }}
      const {{ letterFolder, rangeFolder }} = computeLetterAndRange(last);
      const expandNames = [...BASE_PATH, letterFolder, rangeFolder];

      // 2) Expand down to the range folder
      let currentSearchRoot = document;
      for (const name of expandNames) {{
        const expandedNode = await expand(name, currentSearchRoot);
        currentSearchRoot = expandedNode; // scope subsequent searches
      }}

      // regexes
      const exactRe = buildExactRegex(last, first);
      const lastPlusInitialRe = buildLastPlusFirstInitialRegex(last, first);
      const lastOnlyRe = buildLastOnlyRegex(last);
      const firstLetterRe = buildFirstLetterRegex(last);

      // 3) Try to find exact match first
      try {{
        if (await clickFirstRegex('exact', exactRe, currentSearchRoot, 3000)) {{
          person.found = true;
          person.headshotImgString = getHeadshotImageString(currentSearchRoot);
          continue;
        }}
      }} catch (e) {{
        if (myDebug < myDebugLevels.WARN)
          console.warn('Exact match timed out, trying fallbacks...', e.message);
      }}

      // 4) Fallbacks:
      //   last+first initial,
      //   last only,
      //   first letter of last name

      // last name + first initial
      try {{
        if (await clickFirstRegex('last_first_initial', lastPlusInitialRe, currentSearchRoot, 2000))
          conditionallyModifyPeopleCardData();
          continue;
      }} catch (e) {{
        if (myDebug < myDebugLevels.WARN)
          console.warn(
            'Last+FirstInitial timed out, next fallback...',
            e.message
          );
      }}

      // last name only
      try {{
        if (await clickFirstRegex('lastname_only', lastOnlyRe, currentSearchRoot, 2000))
          conditionallyModifyPeopleCardData();
          continue;
      }} catch (e) {{
        if (myDebug < myDebugLevels.WARN)
          console.warn('Last-only timed out, final fallback...', e.message);
      }}

      // first letter (this should always exist within the range)
      try {{
        if (await clickFirstRegex('first_letter_lastname', firstLetterRe, currentSearchRoot, 2000))
          conditionallyModifyPeopleCardData();
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


def cmd_scan(args, state=None):
    try:
        xlsx_path = _pick_latest_pct_xlsx()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return

    try:
        names = _load_and_strip_names(NAMES_FILE)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return

    try:
        colA_norm = _load_column_a_as_keys(xlsx_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return

    print(f"Using Excel: {os.path.basename(xlsx_path)}")
    print(
        f"Loaded {len(names)} name(s) from {NAMES_FILE} (credentials stripped if present).\n"
    )

    value_to_rows = {}
    for idx, val in colA_norm.items():
        if not val:
            continue
        excel_row = idx + 1
        value_to_rows.setdefault(val, []).append(excel_row)

    total_found = 0
    for name in names:
        variants = _key_variants_from_name(name)
        found_rows = []
        for v in variants:
            if v in value_to_rows:
                found_rows.extend(value_to_rows[v])
        found_rows = sorted(set(found_rows))
        key_display = " OR ".join(variants) if variants else "(unparsable)"
        if found_rows:
            total_found += 1
            print(f"[✅] {name} -> {key_display}  |  Rows: {found_rows}")
        else:
            print(f"[❌] {name} -> {key_display}")

    print(f"\nDone. {total_found}/{len(names)} had at least one match in Column A.")

    names = [
        (first, last)
        for name in names
        if (first := _tokenize_name(name)[0]) and (last := _tokenize_name(name)[2])
    ]
    print(f"\nNames are: names = {names}\n")

    js = _card_finder_js(names)
    try:
        import pyperclip  # type: ignore

        pyperclip.copy(js)
        print("\nJavaScript snippet copied to clipboard.")
    except Exception:
        print("\nInstall pyperclip to enable clipboard copy: pip install pyperclip")
        print("Here is the JavaScript snippet:\n")
        print(js)
