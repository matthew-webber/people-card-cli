import os
import re
from typing import List, Optional, Tuple

from utils.core import debug_print


def load_extracted_people_names(path: str) -> List[str]:
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
            name_only = get_name_before_comma(raw)
            if name_only:
                names.append(name_only)

    return names


def get_name_before_comma(name: str) -> str:
    """Extract the part of the name before any comma (for credentials)."""

    return name.split(",", 1)[0].strip()


def tokenize_name(name: str) -> Tuple[str, Optional[str], str]:

    quote_replaced_name = name.replace("“", '"').replace("”", '"')
    cleaned = re.sub(r"""[^"\w\s\-\.' ]""", " ", quote_replaced_name)
    cleaned = re.sub(
        r"\b(Jr\.?|Sr\.?|II|III|IV|V|M\.?D\.?|Ph\.?D\.?|Esq\.?|B\.?A\.?|B\.?S\.?|M\.?H\.?A\.?|M\.?A\.?|M\.?S\.?|M\.?B\.?A\.?|J\.?D\.?|Ed\.?D\.?|Psy\.?D\.?|D\.?D\.?S\.?|D\.?V\.?M\.?|R\.?N\.?|C\.?P\.?A\.?|D\.Phil|P\.?E\.?)\.?\s*$",
        "",
        cleaned,
        # flags=re.IGNORECASE,
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


def key_variants_from_name(name: str) -> List[str]:
    """
    Generate key variants from a person's name for matching purposes.

    This function tokenizes the input name into first, middle, and last components,
    normalizes them by removing dots, collapsing whitespace, and converting to lowercase,
    then constructs unique key variants in the format 'last-first' and optionally
    'last-middle_initial-first' if a middle name is present.

    Args:
      name (str): The full name string to process.

    Returns:
      List[str]: A list of unique normalized key variants derived from the name.
    """
    first, mid, last = tokenize_name(name)

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
