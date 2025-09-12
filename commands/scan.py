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
import json
from typing import List, Tuple, Optional

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


def _load_extracted_people_names(path: str) -> List[str]:
    """Load names from an extracted people list file, ignoring comments."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found.")

    names: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            # Skip empty lines and comments
            if not raw or raw.startswith("#"):
                continue
            # Split on comma and take first part (in case there are credentials)
            name_only = raw.split(",", 1)[0].strip()
            if name_only:
                names.append(name_only)

    return names


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
  myDebug = 2;
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
    pCardName: null,
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
  const findNodeExact = (name) =>
    Array.from(document.querySelectorAll('.scContentTreeNode')).find(
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

  function waitForMatchExact(name, timeout = 5000) {{
    return new Promise((resolve, reject) => {{
      const start = Date.now();
      (function check() {{
        const m = findNodeExact(name);
        if (m) return resolve(m);
        if (Date.now() - start > timeout)
          return reject(new Error('Timeout waiting for ' + name));
        setTimeout(check, 500);
      }})();
    }});
  }}

  async function expand(name) {{
    const node = await waitForMatchExact(name);
    const arrow = node.querySelector('img');
    if (!arrow) {{
      console.warn('no expand arrow for', name);
      return node;
    }}
    if (myDebug < myDebugLevels.INFO) {{
      console.log('expanding', name, 'found node:', node, 'with arrow:', arrow);
    }}
    if (node.lastElementChild && node.lastElementChild.tagName === 'DIV') {{
      return node;
    }}
    arrow.click();
    await new Promise((r) => setTimeout(r, 250));
    return node;
  }}

  function findNodesByRegex(regex) {{
    const nodes = Array.from(
      document.querySelectorAll('.scContentTreeNode')
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

  function waitForRegex(regex, timeout = 5000) {{
    return new Promise((resolve, reject) => {{
      const start = Date.now();
      (function check() {{
        const matches = findNodesByRegex(regex);
        if (matches.length) return resolve(matches);
        if (Date.now() - start > timeout)
          return reject(new Error('Timeout waiting for regex: ' + regex));
        setTimeout(check, 500);
      }})();
    }});
  }}

  async function clickRegexMatch(regex, timeout = 2500) {{
    const matches = await waitForRegex(regex, timeout);
    const node = matches[0];
    const span = node.querySelector('span');
    if (span) {{
      if (myDebug < myDebugLevels.WARN) {{
        console.log('Clicking node:', span.textContent);
      }}
      span.click();
      return true;
    }} else {{
      console.warn('no span to click for regex match');
      return false;
    }}
  }}

  async function getHeadshotImageString() {{
    let headshotImgStr = null;
    // Find the span whose text contains "Headshot Image" (non-strict match)
    const targetSpan = Array.from(document.querySelectorAll('span')).find(
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
      headshotImgStr = input?.getAttribute('value');
    }} else {{
      console.warn("No span containing 'Headshot Image' found.");
    }}
    if (myDebug < myDebugLevels.WARN) {{
      console.log('Headshot image string:', headshotImgStr);
    }}
    return headshotImgStr || null;
  }}

  const getPeopleCardName = () => {{
    let pCardName = null;
    const scContentTreeNodeActive = document.querySelector('.scContentTreeNodeActive');
    if (scContentTreeNodeActive) {{
        pCardName = scContentTreeNodeActive.textContent.trim();
    }}
    return pCardName;
  }}
      
  for (const person of peopleCardData) {{
    try {{
      // 1) Parse and validate the person's name
      const [first, last] = person.name;
      if (myDebug < myDebugLevels.WARN) {{
        console.log(`Searching for: ${{person.name}} => first: ${{first}}, last: ${{last}}`);
      }}
      if (!first || !last) {{
        console.warn('Skipping unparsable name:', person.name);
        continue;
      }}

      // 2) Compute path and expand to range folder
      const {{ letterFolder, rangeFolder }} = computeLetterAndRange(last);
      const expandNames = [...BASE_PATH, letterFolder, rangeFolder];
      for (const name of expandNames) {{
        await expand(name);
      }}

      // 3) Build regex patterns
      const exactRe = buildExactRegex(last, first);
      const lastPlusInitialRe = buildLastPlusFirstInitialRegex(last, first);
      const lastOnlyRe = buildLastOnlyRegex(last);
      const firstLetterRe = buildFirstLetterRegex(last);

      // Helper function to attempt a match and update person data if successful
      async function attemptMatch(person, scope, regex, timeout) {{
        try {{
          // Fix: avoid stale window.pFound impacting subsequent matches.
          // - For 'exact' scope: if we clicked a match, treat as found immediately.
          // - For other scopes: wait for manual confirmation via countdown() and check window.pFound.
          const clicked = await clickRegexMatch(regex, timeout);
          if (!clicked) return false;

          if (scope === 'exact') {{
            await new Promise((r) => setTimeout(r, 500));
            person.found = true;
            person.pCardName = getPeopleCardName();
            person.headshotImgString = await getHeadshotImageString();
            return true;
          }}

          await countdown(0); // resets window.pFound to null and waits for user input
          if (window.pFound === true) {{
            await new Promise((r) => setTimeout(r, 500)); // waiting for the UI to update...
            person.found = true;
            person.pCardName = getPeopleCardName();
            person.headshotImgString = await getHeadshotImageString();
            return true;
          }} else {{
            if (myDebug < myDebugLevels.WARN) {{
              console.warn(`Skipping headshot grab as pFound is not true for scope "${{scope}}".`);
            }}
          }}
        }} catch (e) {{
          if (myDebug < myDebugLevels.WARN) {{
            console.warn(`Scope of "${{scope}}" match failed:`, e.message);
          }}
        }}
        return false;
      }}

      // 4) Attempt exact match first
      if (await attemptMatch(person, 'exact', exactRe, 3000)) {{
        continue;
      }}

      // 5) Fallback attempts in order
      const fallbacks = [
        {{ scope: 'last_first_initial', regex: lastPlusInitialRe, timeout: 2000 }},
        {{ scope: 'lastname_only', regex: lastOnlyRe, timeout: 2000 }},
        {{ scope: 'first_letter_lastname', regex: firstLetterRe, timeout: 2000 }},
      ];

      let found = false;
      for (const {{ scope, regex, timeout }} of fallbacks) {{
        if (await attemptMatch(person, scope, regex, timeout)) {{
          found = true;
          break;
        }}
      }}

      if (!found) {{
        console.warn('No matches found for:', person.name);
      }}
    }} catch (e) {{
      console.error('Error processing person:', person.name, e);
    }}
  }}
  console.log('People card data results:', peopleCardData);
  
  // Format data for easy copying to CLI
  console.log('\\n' + '='.repeat(60));
  console.log('📋 COPY THE DATA BELOW TO PASTE INTO CLI');
  console.log('='.repeat(60));
  
  // Create delimited format: firstName|lastName|found|headshotImg|pCardName
  const formattedLines = peopleCardData.map(person => {{
    const firstName = person.name[0] || '';
    const lastName = person.name[1] || '';
    const found = person.found ? 'true' : 'false';
    const headshot = person.headshotImgString || '';
    const pCardName = person.pCardName || '';
    
    // Use semicolon as delimiter and escape any semicolons in the data
    return [firstName, lastName, found, headshot, pCardName]
      .map(field => String(field).replace(/;/g, '&#59;'))
      .join(';');
  }}).join('\\n');
  
    console.log(formattedLines);
  console.log('='.repeat(60));
  console.log('💡 Copy all the lines above and paste them into the CLI');
  
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

    # Determine which file to use for names
    names_file = NAMES_FILE
    use_extracted = False

    if state:
        extracted_file = state.get_variable("EXTRACTED_PEOPLE_LIST")
        if extracted_file and os.path.exists(extracted_file):
            names_file = extracted_file
            use_extracted = True
            print(f"📋 Using extracted people list: {os.path.basename(extracted_file)}")
        else:
            print(f"📄 Using default names file: {NAMES_FILE}")

    try:
        if use_extracted:
            names = _load_extracted_people_names(names_file)
        else:
            names = _load_and_strip_names(names_file)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return

    try:
        colA_norm = _load_column_a_as_keys(xlsx_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return

    print(f"Using Excel: {os.path.basename(xlsx_path)}")
    file_type = "extracted people list" if use_extracted else "names file"
    print(
        f"Loaded {len(names)} name(s) from {file_type} (credentials stripped if present).\n"
    )

    value_to_rows = {}
    # Enumerate the normalized Series values to get a guaranteed integer position (1-based Excel row number)
    for pos, val in enumerate(colA_norm.tolist(), start=1):
        if not val:
            continue
        value_to_rows.setdefault(val, []).append(pos)

    total_found = 0
    # After loading names, preserve original list for merging later
    if state is not None:
        state.scan_original_fullnames = list(names)
        state.scan_pct_map = {}
        state.scan_export_rows = []
    # Matching loop
    for name in names:
        variants = _key_variants_from_name(name)
        found_rows = []
        matched_pct_keys = set()
        for v in variants:
            if v in value_to_rows:
                found_rows.extend(value_to_rows[v])
                # Reconstruct approximate PCT raw key base (v) for mapping
                matched_pct_keys.add(v)
        found_rows = sorted(set(found_rows))
        key_display = " OR ".join(variants) if variants else "(unparsable)"
        if found_rows:
            total_found += 1
            print(f"[✅] {name} -> {key_display}  |  Rows: {found_rows}")
            if state is not None:
                first, _, last = _tokenize_name(name)
                k = (first.lower(), last.lower())
                bucket = state.scan_pct_map.setdefault(k, set())
                bucket.update(matched_pct_keys)
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
        print("\n✅ JavaScript snippet copied to clipboard.")
    except Exception:
        print("\n⚠️  Install pyperclip to enable clipboard copy: pip install pyperclip")
        print("Here is the JavaScript snippet:\n")
        print(js)

    # Paste input mode
    print("\n" + "=" * 60)
    print("📋 PASTE MODE ACTIVATED")
    print("=" * 60)
    print("📋 JavaScript has been copied to clipboard")
    print("🌐 Paste and run it in your browser's developer console")
    print("📄 Copy the delimited data from the console output")
    print("📥 Paste it below when prompted")
    print("🚫 Press Ctrl+C to cancel and return to CLI")
    print("=" * 60)

    try:
        print("\n💡 After running the JavaScript, paste the delimited data here:")
        print("(End with an empty line or Ctrl+D)")

        pasted_lines = []
        while True:
            try:
                line = input()
                if not line.strip():  # Empty line ends input
                    break
                pasted_lines.append(line.strip())
            except EOFError:  # Ctrl+D
                break

        if pasted_lines:
            # Process the pasted data (pass state explicitly)
            _process_pasted_data(pasted_lines, state)
        else:
            print("⚠️  No data provided")

    except KeyboardInterrupt:
        print("\n🚫 Operation cancelled by user")
    finally:
        print("\n🏁 Scan command completed")


def _process_pasted_data(lines, state=None):
    """Process and display pasted delimited people card data."""
    print("\n" + "=" * 60)
    print("📊 PROCESSING PASTED PEOPLE CARD DATA")
    print("=" * 60)

    # Print raw data for sanity check
    print("🔍 Raw pasted data:")
    for i, line in enumerate(lines, 1):
        print(f"  {i:2d}: {line}")
    print("\n" + "-" * 60)

    # First, handle the case where data might be on a single line with \n separators
    all_lines = []
    for line in lines:
        # Split on literal \n if it exists, otherwise treat as single line
        if "\\n" in line:
            # Handle literal \n separators
            split_lines = line.split("\\n")
            all_lines.extend(split_lines)
        else:
            all_lines.append(line)

    # Remove empty lines
    all_lines = [line.strip() for line in all_lines if line.strip()]

    print(f"📝 Parsed into {len(all_lines)} individual records:")
    for i, line in enumerate(all_lines, 1):
        print(f"  {i:2d}: {line}")
    print("\n" + "-" * 60)

    # Parse delimited data
    parsed_people = []
    for line_num, line in enumerate(all_lines, 1):
        try:
            # Split by semicolon and unescape
            parts = [part.replace("&#59;", ";") for part in line.split(";")]

            if len(parts) >= 3:
                first_name = parts[0] if len(parts) > 0 else ""
                last_name = parts[1] if len(parts) > 1 else ""
                found = parts[2].lower() == "true" if len(parts) > 2 else False
                headshot = parts[3] if len(parts) > 3 else ""
                pcard_name = parts[4] if len(parts) > 4 else ""

                parsed_people.append(
                    {
                        "name": [first_name, last_name],
                        "found": found,
                        "headshotImgString": headshot if headshot else None,
                        "pCardName": pcard_name if pcard_name else None,
                    }
                )
            else:
                print(f"⚠️  Line {line_num} has too few fields, skipping: {line}")

        except Exception as e:
            print(f"❌ Error parsing line {line_num}: {e}")
            print(f"   Line content: {line}")

    # Process the parsed data using existing function
    if parsed_people:
        _process_received_data(parsed_people, state=state)
    else:
        print("❌ No valid data could be parsed from the input")


def _process_received_data(data, state=None):
    """Process and display the received people card data.

    state: optional CLIState instance explicitly passed from caller. Passing explicitly
    avoids brittle reliance on global lookups that could fail depending on invocation context.
    """
    active_state = state

    print("\n" + "=" * 60)
    print("📊 RECEIVED PEOPLE CARD DATA")
    print("=" * 60)

    # Print raw data for sanity check as requested
    print("🔍 Raw data received:")
    print(json.dumps(data, indent=2))
    print("\n" + "-" * 60)

    # Process and summarize the data
    total_people = len(data)
    found_count = sum(1 for person in data if person.get("found", False))

    print(f"📈 SUMMARY:")
    print(f"   Total people processed: {total_people}")
    print(f"   People found: {found_count}")
    print(f"   People not found: {total_people - found_count}")

    print(f"\n📋 DETAILED RESULTS:")
    export_rows = []

    for i, person in enumerate(data, 1):
        name = person.get("name", ["Unknown", "Unknown"])  # [first,last]
        found = person.get("found", False)
        headshot = person.get("headshotImgString")
        pcard = person.get("pCardName")

        first = name[0] if isinstance(name, list) and len(name) > 0 else ""
        last = name[1] if isinstance(name, list) and len(name) > 1 else ""
        key = (first.lower(), last.lower())
        pct_keys = []
        if active_state is not None and hasattr(active_state, "scan_pct_map"):
            pct_keys = sorted(active_state.scan_pct_map.get(key, []))

        status = "✅ FOUND" if found else "❌ NOT FOUND"
        name_display = f"{first} {last}".strip()
        print(f"   {i:2d}. {status} - {name_display}")
        if pct_keys:
            print(f"       🔑 PCT Keys: {', '.join(pct_keys)}")
        if found and headshot:
            headshot_preview = headshot[:70] + ("..." if len(headshot) > 70 else "")
            print(f"       🖼️  Headshot: {headshot_preview}")
        if pcard:
            print(f"       📛 Sitecore Name: {pcard}")

        # Build export rows (one row per PCT key if present, else one placeholder row)
        if pct_keys:
            for pct_key in pct_keys:
                export_rows.append(
                    {
                        "Name (PCT)": pct_key,
                        "Full Name": name_display,
                        "Headshot String": headshot or "",
                        "Name (Sitecore)": pcard or "",
                    }
                )
        else:
            export_rows.append(
                {
                    "Name (PCT)": "",
                    "Full Name": name_display,
                    "Headshot String": headshot or "",
                    "Name (Sitecore)": pcard or "",
                }
            )

    print("=" * 60)

    # Store export rows in state for later save
    if active_state is not None:
        active_state.scan_export_rows = export_rows
        print(f"💾 Prepared {len(export_rows)} row(s) for export.")
        # Offer immediate export only if there are rows
        if export_rows:
            try:
                choice = input("📝 Export to Excel now? [Y/n]: ").strip().lower()
            except KeyboardInterrupt:
                choice = "n"
            if choice in ("", "y", "yes"):
                _export_scan_results_to_excel(active_state)


def _export_scan_results_to_excel(state):
    """Write the scan_export_rows to an Excel file."""
    rows = getattr(state, "scan_export_rows", [])

    domain = state.get_variable("DOMAIN") if state else "domain"
    row = state.get_variable("ROW") if state else "row"

    if not rows:
        print("⚠️  No export rows available.")
        return
    try:
        import pandas as pd
    except ImportError:
        print("❌ pandas is required to export Excel. Install with: pip install pandas")
        return
    import datetime
    from pathlib import Path

    df = pd.DataFrame(
        rows, columns=["Name (PCT)", "Full Name", "Headshot String", "Name (Sitecore)"]
    )
    exports_dir = Path("people_reports")
    exports_dir.mkdir(exist_ok=True)
    fname = exports_dir / f"{domain}_{row}.xlsx"
    try:
        df.to_excel(fname, index=False)
        print(f"✅ Export written: {fname}")
    except Exception as e:
        print(f"❌ Failed to write export: {e}")
