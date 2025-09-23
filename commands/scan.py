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
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Tuple, Optional

import requests

from utils.people_names import (
    load_extracted_people_names,
    key_variants_from_name,
    tokenize_name,
)
from utils.scraping import get_page_soup

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


def _normalize_for_match(text: Optional[str]) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", ascii_str.lower())


def _is_placeholder_headshot(headshot: Optional[str]) -> bool:
    if not headshot:
        return False
    needle = headshot.strip().lower()
    if not needle:
        return False
    return (
        needle == "headshots/p/p_placeholder"
        or "target" in needle
        or "placeholder" in needle
    )


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
  window.pFound = null; // global flag to be set manually in console
  window.nameSearchingFor = null; // current name being searched for

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
      if (window.nameSearchingFor) {{
        console.log(`🔎 Search for: ${{window.nameSearchingFor}}`);
      }}
      console.log('***DIRECTIONS***');
      console.log('1. Set window.pFound = true in the console to grab the headshot string.');
      console.log('2. If person not found, set window.pFound = false to skip.');
      console.log('3. If nothing happens after 30s, the script will continue automatically.');
      while (window.pFound === null && num_waits < 10) {{
        if (window.nameSearchingFor) {{
          console.log(`Waiting... (target: ${{window.nameSearchingFor}})`);
        }} else {{
          console.log('Waiting...');
        }}
        await new Promise((resolve) => setTimeout(resolve, 3000));
        num_waits++;
      }}
      console.log(`${{window.pFound === true ? '✅ Proceeding with data of currently selected person.' : window.pFound === false ? '❌ Skipping to next person.' : '⌛️ Timeout reached without confirmation, skipping.'}}`);
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
      // update global hint for the user during manual countdowns
      window.nameSearchingFor = `${{first}} ${{last}}`;
      if (myDebug < myDebugLevels.WARN) {{
        console.log(`Searching for: ${{person.name}} => first: ${{first}}, last: ${{last}}`);
        console.log(`nameSearchingFor set to: ${{window.nameSearchingFor}}`);
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
            await new Promise((r) => setTimeout(r, 2000));
            person.found = true;
            person.pCardName = getPeopleCardName();
            person.headshotImgString = await getHeadshotImageString();
            return true;
          }} else {{
            const [first, last] = person.name;
            switch (scope) {{
              case 'last_first_initial':
                console.log(`Matched last + first initial: ${{last.toUpperCase()}}, ${{first.charAt(0).toUpperCase()}}`);
                break;

              case 'lastname_only':
                console.log(`Matched last: ${{last.toUpperCase()}}`);
                break;

              case 'first_letter_lastname':
                console.log(`Matched first letter of last name: ${{last.charAt(0).toUpperCase()}}`);
                break;
              default:
                break;
            }}
          }}

          await countdown(0); // resets window.pFound to null and waits for user input
          if (window.pFound === true) {{
            await new Promise((r) => setTimeout(r, 2200)); // waiting for the UI to update...
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
          window.pFound = null; // reset before each attempt
          if (myDebug < myDebugLevels.WARN) {{
            console.log(`Attempting fallback scope: ${{scope}} with regex: ${{regex}}`);
          }}

        found = await attemptMatch(person, scope, regex, timeout);

        if (found || window.pFound === false) {{
          if (myDebug < myDebugLevels.WARN) {{
            console.log(`Found: ${{found}}, pFound: ${{window.pFound}} after scope: ${{scope}}`);
          }}
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

    try:

        if state:
            extracted_file = state.get_variable("EXTRACTED_PEOPLE_LIST")
            print(f"DEBUG: extracted_file from state: {extracted_file}")
            if extracted_file and os.path.exists(extracted_file):
                names = load_extracted_people_names(extracted_file)
                print(
                    f"📋 Using extracted people list: {os.path.basename(extracted_file)}"
                )
                print(f"DEBUG: use_extracted set to True")
            else:
                # raise FileNotFoundError if the file doesn't exist
                raise FileNotFoundError
        else:
            raise FileNotFoundError

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return

    try:
        colA_norm = _load_column_a_as_keys(xlsx_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return

    print(f"Using Excel: {os.path.basename(xlsx_path)}")
    file_type = "extracted people list"
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
        variants = key_variants_from_name(name)
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
                first, _, last = tokenize_name(name)
                k = (first.lower(), last.lower())
                bucket = state.scan_pct_map.setdefault(k, set())
                bucket.update(matched_pct_keys)
        else:
            print(f"[❌] {name} -> {key_display}")

    print(f"\nDone. {total_found}/{len(names)} had at least one match in Column A.")

    names = [
        (first, last)
        for name in names
        if (first := tokenize_name(name)[0]) and (last := tokenize_name(name)[2])
    ]

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
        # At the end of the scan command, print TODOs for placeholder headshots if any were detected
        try:
            if state is not None:
                placeholders = getattr(state, "scan_placeholder_headshots", None)
                if placeholders:
                    print("\n" + "=" * 60)
                    print("🧩 TODO")
                    print("=" * 60)
                    print(
                        "The following people have placeholder headshots (Headshots/P/p_placeholder):"
                    )
                    for entry in placeholders:
                        name = entry.get("name_display") or "Unknown"
                        print(f"  - {name}")
                    print(
                        "Please update these headshots in Sitecore before finalizing the export."
                    )
        except Exception:
            # Don't let this best-effort summary interfere with command completion
            pass
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
    placeholder_headshots = []  # Track any people with placeholder headshots
    download_targets = []

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

        is_placeholder = _is_placeholder_headshot(headshot)

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

        if (not found) or is_placeholder:
            download_targets.append(
                {
                    "first": first,
                    "last": last,
                    "name_display": name_display,
                    "pct_keys": pct_keys,
                }
            )

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

        # Capture placeholder headshots for end-of-command TODO summary
        hs_norm = (headshot or "").strip().lower()
        if hs_norm == "headshots/p/p_placeholder":
            placeholder_headshots.append(
                {
                    "first": first,
                    "last": last,
                    "name_display": name_display,
                }
            )

    print("=" * 60)

    # Store export rows and placeholder summary in state for later use
    if active_state is not None:
        active_state.scan_export_rows = export_rows
        active_state.scan_placeholder_headshots = placeholder_headshots
        print(f"💾 Prepared {len(export_rows)} row(s) for export.")
        # Offer immediate export only if there are rows
        if export_rows:
            # try:
            #   choice = input("📝 Export to Excel now? [Y/n]: ").strip().lower()
            # except KeyboardInterrupt:
            #   choice = "n"
            # if choice in ("", "y", "yes"):
            _export_scan_results_to_excel(active_state)

            if download_targets:
                _download_headshots_for_targets(active_state, download_targets)


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


def _download_headshots_for_targets(state, targets):
    """Attempt to download headshots for people who need them."""

    if not targets:
        return

    if state is None or not hasattr(state, "get_variable"):
        print("\n⚠️  State unavailable; skipping headshot scrape.")
        return

    existing_urls = state.get_variable("EXISTING_URLS") or []
    if not existing_urls:
        print("\n⚠️  No EXISTING_URLS available; skipping headshot scrape.")
        return

    print("\n" + "=" * 60)
    print("🖼️  HEADSHOT SCRAPE")
    print("=" * 60)

    page_cache = {}
    for url in existing_urls:
        try:
            soup, response = get_page_soup(url)
            page_cache[url] = (soup, response)
        except (
            Exception
        ) as exc:  # pragma: no cover - network errors only shown at runtime
            print(f"⚠️  Failed to fetch {url}: {exc}")

    if not page_cache:
        print("❌ Unable to fetch any EXISTING_URLS; skipping headshot scrape.")
        return

    headshots_dir = Path("headshots")
    headshots_dir.mkdir(exist_ok=True)

    def slugify_name(first: str, last: str) -> str:
        def clean(part: Optional[str]) -> str:
            if not part:
                return ""
            normalized = unicodedata.normalize("NFKD", part)
            ascii_part = normalized.encode("ascii", "ignore").decode("ascii")
            return re.sub(r"[^a-z0-9]+", "-", ascii_part.lower()).strip("-")

        pieces = [clean(last), clean(first)]
        joined = "-".join([p for p in pieces if p])
        return joined or "headshot"

    for target in targets:
        first = target.get("first", "")
        last = target.get("last", "")
        name_display = target.get("name_display") or f"{first} {last}".strip()
        pct_keys = target.get("pct_keys") or []

        last_norm = _normalize_for_match(last)
        if not last_norm:
            print(f"⚠️  Skipping {name_display}: no last name available for matching.")
            continue

        matches = []
        seen = set()
        for _, (soup, response) in page_cache.items():
            for img in soup.find_all("img"):
                alt = img.get("alt")
                if not alt:
                    continue
                alt_norm = _normalize_for_match(alt)
                if not alt_norm or last_norm not in alt_norm:
                    continue
                src = img.get("src") or ""
                if not src:
                    continue
                absolute_src = urljoin(response.url, src)
                key = (absolute_src, alt)
                if key in seen:
                    continue
                seen.add(key)
                matches.append({"src": absolute_src, "alt": alt})

        if not matches:
            print(f"⚠️  No matching headshot found for {name_display}.")
            continue

        filename_stem = pct_keys[0] if pct_keys else slugify_name(first, last)
        filename_stem = filename_stem or slugify_name(first, last)

        for match in matches:
            src = match["src"]
            alt = match.get("alt") or "(no alt)"
            print("\nFound candidate image for", name_display)
            print(f"  Alt: {alt}")
            print(f"  Src: {src}")

            try:
                choice = input("Save this image? [Y/n]: ").strip().lower()
            except KeyboardInterrupt:
                print("\n↪️  Headshot scraping cancelled by user.")
                return

            if choice not in ("", "y", "yes"):
                print("↪️  Skipping this image.")
                continue

            try:
                response = requests.get(src, timeout=30)
                response.raise_for_status()
            except requests.RequestException as exc:  # pragma: no cover - network
                print(f"❌ Failed to download image: {exc}")
                continue

            ext = os.path.splitext(urlparse(src).path)[1]
            if not ext:
                content_type = (response.headers.get("Content-Type") or "").lower()
                if "png" in content_type:
                    ext = ".png"
                elif "gif" in content_type:
                    ext = ".gif"
                elif "webp" in content_type:
                    ext = ".webp"
                else:
                    ext = ".jpg"

            output_path = headshots_dir / f"{filename_stem}{ext}"

            if output_path.exists():
                try:
                    overwrite = (
                        input(f"⚠️  {output_path} exists. Overwrite? [y/N]: ")
                        .strip()
                        .lower()
                    )
                except KeyboardInterrupt:
                    print("\n↪️  Headshot scraping cancelled by user.")
                    return
                if overwrite not in ("y", "yes"):
                    print("↪️  Keeping existing file; skipping save.")
                    continue

            try:
                with open(output_path, "wb") as fh:
                    fh.write(response.content)
                print(f"✅ Saved headshot to {output_path}")
            except OSError as exc:
                print(f"❌ Failed to write {output_path}: {exc}")
                continue

            break
        else:
            print(f"⚠️  No image saved for {name_display}.")
