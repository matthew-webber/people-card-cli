// JavaScript snippet to find a person card by name on a webpage
(async () => {
  // --- DEBUG SETUP ---
  myDebug = 3;
  myDebugLevels = {
    DEBUG: 1,
    INFO: 2,
    WARN: 3,
  };

  // --- INPUT: person full name as "first_name last_name" ---
  // Prompt for name, remembering last entry in localStorage
  // const lastPerson = localStorage.getItem('lastPersonName') || 'John Smith';
  // const personName = prompt("Enter person's name (first last):", lastPerson);

  // Check if names were provided from Python script
  const providedNames = { names };

  if (!providedNames.length > 0) {
    console.error('No names provided from Python script.');
    return;
  }

  const peopleCardData = providedNames.map((name) => ({
    name,
    found: false,
    headshotImgString: null,
  }));

  // --- Helpers ---
  const sanitizeName = (name) =>
    String(name || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/\p{Diacritic}/gu, '')
      .replace(/[-_]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

  const canonicalKebab = (s) =>
    String(s || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/\p{Diacritic}/gu, '')
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');

  function parsePersonName(full) {
    const s = sanitizeName(full);
    const parts = s.split(' ');
    if (parts.length < 2) {
      throw new Error('Expected "first last" but got: ' + full);
    }
    const first = parts[0];
    const last = parts.slice(1).join(' ');
    return { first, last };
  }

  async function countdown(seconds) {
    // if seconds === 0, wait until window.userReady === true
    if (seconds === 0) {
      window.userReady = false;
      let num_waits = 0;
      console.log('Waiting for userReady to be true...');
      while (!window.userReady && num_waits < 12) {
        console.log('Waiting...');
        await new Promise((resolve) => setTimeout(resolve, 5000));
        num_waits++;
      }
      console.log('userReady is now true.');
      return;
    }
    for (let i = seconds; i > 0; i--) {
      console.log(`Moving to next provider in ${i}...`);
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  const BASE_PATH = [
    'Redesign Data',
    'Modules Global Data',
    'People Cards',
    'People Card Data',
  ];

  function computeLetterAndRange(last) {
    const clean = canonicalKebab(last).replace(/-/g, '');
    const firstLetter = (clean[0] || '').toUpperCase();
    if (!firstLetter || !/[A-Z]/.test(firstLetter)) {
      throw new Error('Last name must start with A-Z: ' + last);
    }
    const secondLetter = (clean[1] || 'a').toLowerCase();
    let bucketStart, bucketEnd;
    if (secondLetter >= 'a' && secondLetter <= 'i') {
      bucketStart = 'a';
      bucketEnd = 'i';
    } else if (secondLetter >= 'j' && secondLetter <= 'r') {
      bucketStart = 'j';
      bucketEnd = 'r';
    } else {
      bucketStart = 's';
      bucketEnd = 'z';
    }
    const letterFolder = firstLetter; // e.g. "S"
    const rangeFolder = `${firstLetter}${bucketStart}-${firstLetter}${bucketEnd}`; // e.g. "Sj-Sr"
    return { letterFolder, rangeFolder };
  }

  function buildExactRegex(last, first) {
    const lastK = canonicalKebab(last);
    const firstK = canonicalKebab(first);
    const pattern = `^${lastK}-${firstK}-\\d{4}$`;
    if (myDebug < myDebugLevels.WARN) console.log('Exact regex:', pattern);
    return new RegExp(pattern, 'i');
  }

  function buildLastPlusFirstInitialRegex(last, first) {
    const lastK = canonicalKebab(last);
    const firstInitial = canonicalKebab(first).charAt(0) || '';
    // allow hyphens in first-name remainder, keep required 4 digits at end
    const pattern = `^${lastK}-${firstInitial}[a-z0-9-]*-\\d{4}$`;
    if (myDebug < myDebugLevels.WARN)
      console.log('Last+FirstInitial regex:', pattern);
    return new RegExp(pattern, 'i');
  }

  function buildLastOnlyRegex(last) {
    const lastK = canonicalKebab(last);
    const pattern = `^${lastK}-[a-z0-9-]+-\\d{4}$`;
    if (myDebug < myDebugLevels.WARN) console.log('Last-only regex:', pattern);
    return new RegExp(pattern, 'i');
  }

  function buildFirstLetterRegex(last) {
    const letter = (canonicalKebab(last)[0] || '').toLowerCase();
    const pattern = `^${letter}[a-z0-9-]*-\\d{4}$`;
    if (myDebug < myDebugLevels.WARN)
      console.log('First-letter regex:', pattern);
    return new RegExp(pattern, 'i');
  }

  // --- Tree search utils ---
  const findNodeExact = (name, searchRoot = document) =>
    Array.from(searchRoot.querySelectorAll('.scContentTreeNode')).find(
      (node) => {
        const target = sanitizeName(name);
        const span = node.querySelector('span');
        if (!span) {
          console.warn('no span for', name);
          return false;
        }
        if (myDebug < myDebugLevels.INFO) {
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
        }
        return span && sanitizeName(span.textContent) === target;
      }
    );

  function waitForMatchExact(name, searchRoot = document, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      (function check() {
        const m = findNodeExact(name, searchRoot);
        if (m) return resolve(m);
        if (Date.now() - start > timeout)
          return reject(new Error('Timeout waiting for ' + name));
        setTimeout(check, 500);
      })();
    });
  }

  async function expand(name, searchRoot = document) {
    const node = await waitForMatchExact(name, searchRoot);
    const arrow = node.querySelector('img');
    if (!arrow) {
      console.warn('no expand arrow for', name);
      return node;
    }
    if (myDebug < myDebugLevels.WARN) {
      console.log('expanding', name, 'found node:', node, 'with arrow:', arrow);
    }
    if (node.lastElementChild && node.lastElementChild.tagName === 'DIV') {
      console.log('already expanded', name);
      return node;
    }
    arrow.click();
    await new Promise((r) => setTimeout(r, 250));
    return node;
  }

  function findNodesByRegex(regex, searchRoot = document) {
    const nodes = Array.from(
      searchRoot.querySelectorAll('.scContentTreeNode')
    ).filter((node) => {
      const span = node.querySelector('span');
      if (!span) return false;
      const txt = (span.textContent || '').trim();
      const ok = regex.test(txt);
      if (myDebug < myDebugLevels.INFO) {
        console.log('Testing node text:', txt, 'against', regex, '=>', ok);
      }
      return ok;
    });
    return nodes;
  }

  function waitForRegex(regex, searchRoot = document, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      (function check() {
        const matches = findNodesByRegex(regex, searchRoot);
        if (matches.length) return resolve(matches);
        if (Date.now() - start > timeout)
          return reject(new Error('Timeout waiting for regex: ' + regex));
        setTimeout(check, 500);
      })();
    });
  }

  async function clickFirstRegex(regex, searchRoot = document, timeout = 2500) {
    const matches = await waitForRegex(regex, searchRoot, timeout);
    const node = matches[0];
    const span = node.querySelector('span');
    if (span) {
      if (myDebug < myDebugLevels.WARN) {
        console.log('Clicking node:', span.textContent);
      }
      span.click();
      await countdown(0);
      return true;
    } else {
      console.warn('no span to click for regex match');
      return false;
    }
  }

  function getHeadshotImageString(searchRoot = document) {
    // Find the span whose text contains "Headshot Image" (non-strict match)
    const targetSpan = Array.from(searchRoot.querySelectorAll('span')).find(
      (span) => (span.textContent || '').includes('Headshot Image')
    );

    if (targetSpan) {
      // Step 1: get the parent of that span
      const parent = targetSpan.parentElement;
      // Step 2: get the next sibling element
      const sibling = parent?.nextElementSibling;
      // Step 3: find the input inside that sibling
      const input = sibling?.querySelector('input');
      // Step 4: get the value attribute
      const val = input?.getAttribute('value');
    } else {
      console.warn("No span containing 'Headshot Image' found.");
    }
    return val || null;
  }

  for (const person of peopleCardData) {
    try {
      // 1) Parse, compute path
      const { first, last } = parsePersonName(person.name);
      const { letterFolder, rangeFolder } = computeLetterAndRange(last);
      const expandNames = [...BASE_PATH, letterFolder, rangeFolder];

      // 2) Expand down to the range folder
      let currentSearchRoot = document;
      for (const name of expandNames) {
        const expandedNode = await expand(name, currentSearchRoot);
        currentSearchRoot = expandedNode; // scope subsequent searches
      }

      // 3) Try exact, then fallbacks
      const exactRe = buildExactRegex(last, first);
      const lastPlusInitialRe = buildLastPlusFirstInitialRegex(last, first);
      const lastOnlyRe = buildLastOnlyRegex(last);
      const firstLetterRe = buildFirstLetterRegex(last);

      // exact
      try {
        if (await clickFirstRegex(exactRe, currentSearchRoot, 3000)) {
          person.found = true;
          person.headshotImgString = getHeadshotImageString(currentSearchRoot);
          continue;
        }
      } catch (e) {
        if (myDebug < myDebugLevels.WARN)
          console.log('Exact match timed out, trying fallbacks...', e.message);
      }

      // last + first initial
      try {
        if (await clickFirstRegex(lastPlusInitialRe, currentSearchRoot, 2000))
          continue;
      } catch (e) {
        if (myDebug < myDebugLevels.WARN)
          console.log(
            'Last+FirstInitial timed out, next fallback...',
            e.message
          );
      }

      // last name only
      try {
        if (await clickFirstRegex(lastOnlyRe, currentSearchRoot, 2000))
          continue;
      } catch (e) {
        if (myDebug < myDebugLevels.WARN)
          console.log('Last-only timed out, final fallback...', e.message);
      }

      // first letter (this should always exist within the range)
      try {
        if (await clickFirstRegex(firstLetterRe, currentSearchRoot, 2000))
          continue;
      } catch (e) {
        console.warn(
          'First-letter fallback timed out; nothing clickable matched expected patterns.'
        );
      }
    } catch (e) {
      console.error(e);
    }
  }
  console.log('People card data results:', peopleCardData);
  return peopleCardData;
})();
