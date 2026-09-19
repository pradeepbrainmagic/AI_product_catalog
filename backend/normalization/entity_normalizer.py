from __future__ import annotations

import json
import re
from pathlib import Path
from rapidfuzz import process, fuzz


# =========================================================
# Configuration
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
ABBREVIATIONS_FILE = BASE_DIR / "abbreviations.json"
SPELLING_VARIANTS_FILE = BASE_DIR / "spelling_variants.json"

def _load_abbreviations() -> dict:
    """
    Load field-scoped abbreviations from abbreviations.json.

    Only abbreviation -> canonical DB value mappings belong here.
    Typos, half words and natural short forms are resolved dynamically
    against the candidates supplied by the DatabaseLayer.
    """
    try:
        with ABBREVIATIONS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data.get("fields", {})
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _load_spelling_variants() -> dict:
    """
    Load dataset-derived spelling variants.

    The JSON contains only variant -> canonical database value
    mappings for the supported fields.

    The canonical target is always verified against the current
    candidate list before it is accepted.
    """
    try:
        with SPELLING_VARIANTS_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data.get("fields", {})

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        OSError
    ):

        return {}
    
ABBREVIATIONS = _load_abbreviations()
SPELLING_VARIANTS = _load_spelling_variants()
# =========================================================
# Text Normalization
# =========================================================

def clean_text(value: str) -> str:
    """Normalize text for comparison."""
    if value is None:
        return ""

    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def compact_text(value: str) -> str:
    """Remove spaces/symbols so short forms can be compared robustly."""
    return re.sub(r"[^a-z0-9]", "", clean_text(value))


def _field_key(entity_type: str) -> str:
    """
    Convert the entity type received by the existing pipeline into the
    canonical abbreviation JSON field name.

    No dataset values are hardcoded here.
    """
    value = clean_text(entity_type)

    aliases = {
        "oem": "oem",
        "model": "model",
        "engine": "engine",
        "year": "year",
        "producttype": "producttype",
        "product type": "producttype",
        "category": "category",
    }

    return aliases.get(value, value.replace(" ", ""))


# =========================================================
# Exact Match
# =========================================================

def exact_match(user_value, candidates):
    cleaned_input = clean_text(user_value)

    if not cleaned_input:
        return None

    for candidate in candidates:
        if clean_text(candidate) == cleaned_input:
            return {
                "matched_value": candidate,
                "confidence": 100,
                "method": "exact_match",
            }

    return None


# =========================================================
# Abbreviation Match
# =========================================================

def abbreviation_match(user_value, candidates, entity_type):
    """
    Resolve only explicit abbreviations from abbreviations.json.

    The canonical target must also exist in the current candidate set.
    This prevents an abbreviation mapping from forcing a value that is
    not valid for the current database search context.
    """
    cleaned_input = clean_text(user_value)
    field = _field_key(entity_type)

    if not cleaned_input:
        return None

    field_abbreviations = ABBREVIATIONS.get(field, {})

    target = None

    for alias, canonical in field_abbreviations.items():
        if clean_text(alias) == cleaned_input:
            target = canonical
            break

    if target is None:
        return None

    target_match = exact_match(target, candidates)

    if not target_match:
        return None

    return {
        "matched_value": target_match["matched_value"],
        "confidence": 98,
        "method": "abbreviation_match",
        "abbreviation": user_value,
    }

# =========================================================
# Spelling Variant Match
# =========================================================

def spelling_variant_match(
    user_value,
    candidates,
    entity_type
):
    """
    Resolve known spelling mistakes / spelling variants from
    spelling_variants.json.

    The JSON is dataset-derived, but the canonical value is
    accepted only when it exists in the current candidate set.

    This prevents the JSON from forcing an invalid value into
    the current database context.
    """

    cleaned_input = clean_text(user_value)

    if not cleaned_input:
        return None

    field = _field_key(entity_type)

    field_variants = (
        SPELLING_VARIANTS.get(
            field,
            {}
        )
    )

    if not field_variants:
        return None

    target = None

    for variant, canonical in field_variants.items():

        if clean_text(variant) == cleaned_input:

            target = canonical
            break

    if target is None:
        return None

    # -----------------------------------------------------
    # Verify canonical value exists in current candidates
    # -----------------------------------------------------

    target_match = exact_match(
        target,
        candidates
    )

    if not target_match:
        return None

    return {
        "matched_value":
            target_match["matched_value"],

        "confidence":
            97,

        "method":
            "spelling_variant_match",

        "spelling_variant":
            user_value
    }
# =========================================================
# Prefix / Half-Word Match
# =========================================================

def prefix_match(user_value, candidates):
    """
    Resolve a unique meaningful prefix against actual DB candidates.

    This is dynamic: no catalog value is stored in Python.
    Very short inputs are intentionally rejected to avoid false matches.
    """
    cleaned_input = clean_text(user_value)
    compact_input = compact_text(user_value)

    if len(compact_input) < 3:
        return None

    matches = []

    for candidate in candidates:
        candidate_clean = clean_text(candidate)
        candidate_compact = compact_text(candidate)

        if not candidate_compact:
            continue

        # Word-prefix match, e.g. "freight" -> "Freightliner"
        words = candidate_clean.split()
        if any(word.startswith(cleaned_input) for word in words):
            matches.append(candidate)
            continue

        # Compact prefix match for values such as model/engine strings.
        if candidate_compact.startswith(compact_input):
            matches.append(candidate)

    unique_matches = list(dict.fromkeys(matches))

    if len(unique_matches) == 1:
        return {
            "matched_value": unique_matches[0],
            "confidence": 93,
            "method": "prefix_match",
        }

    if len(unique_matches) > 1:
        return {
            "matched_value": None,
            "confidence": 0,
            "method": "ambiguous",
            "candidates": unique_matches[:10],
        }

    return None


# =========================================================
# Partial / Half Name Match
# =========================================================

def partial_match(user_value, candidates):
    cleaned_input = clean_text(user_value)
    compact_input = compact_text(user_value)

    if len(compact_input) < 3:
        return None

    matches = []

    for candidate in candidates:
        cleaned_candidate = clean_text(candidate)
        compact_candidate = compact_text(candidate)

        if (
            cleaned_input in cleaned_candidate
            or cleaned_candidate in cleaned_input
            or compact_input in compact_candidate
            or compact_candidate in compact_input
        ):
            matches.append(candidate)

    unique_matches = list(dict.fromkeys(matches))

    if len(unique_matches) == 1:
        return {
            "matched_value": unique_matches[0],
            "confidence": 90,
            "method": "partial_match",
        }

    if len(unique_matches) > 1:
        return {
            "matched_value": None,
            "confidence": 0,
            "method": "ambiguous",
            "candidates": unique_matches[:10],
        }

    return None


# =========================================================
# Fuzzy Match
# =========================================================

def fuzzy_match(user_value, candidates, score_cutoff=70):
    """
    Dynamic fuzzy resolution against the current DB candidates.

    Multiple similarity signals are considered so ordinary typos and
    shortened natural input work better than WRatio alone.
    """
    cleaned_input = clean_text(user_value)
    compact_input = compact_text(user_value)

    if len(compact_input) < 3:
        return None

    candidate_map = {}

    for candidate in candidates:
        cleaned = clean_text(candidate)
        if cleaned:
            candidate_map.setdefault(cleaned, candidate)

    if not candidate_map:
        return None

    cleaned_keys = list(candidate_map.keys())

    # WRatio is useful for general spelling differences.
    wratio_results = process.extract(
        cleaned_input,
        cleaned_keys,
        scorer=fuzz.WRatio,
        limit=5,
    )

    # Partial ratio helps when the user provides only part of a value.
    partial_results = process.extract(
        cleaned_input,
        cleaned_keys,
        scorer=fuzz.partial_ratio,
        limit=5,
    )

    scored = {}

    for matched, score, _ in wratio_results:
        scored[matched] = max(scored.get(matched, 0), float(score))

    for matched, score, _ in partial_results:
        # Partial matches are useful, but should not dominate a full match
        # when they are based on a very small fragment.
        adjusted = float(score)

        if len(compact_input) < 5:
            adjusted = min(adjusted, 88)

        scored[matched] = max(scored.get(matched, 0), adjusted)

    ranked = sorted(
        scored.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    if not ranked:
        return None

    best_key, best_score = ranked[0]

    if best_score < score_cutoff:
        return None

    matches = [
        {
            "value": candidate_map[key],
            "score": round(score, 2),
        }
        for key, score in ranked[:3]
    ]

    # Require a meaningful gap when two candidates are close.
    if len(ranked) > 1:
        second_score = ranked[1][1]

        if best_score - second_score < 5:
            return {
                "matched_value": None,
                "confidence": round(best_score, 2),
                "method": "ambiguous",
                "candidates": matches,
            }

    return {
        "matched_value": candidate_map[best_key],
        "confidence": round(best_score, 2),
        "method": "fuzzy_match",
        "candidates": matches,
    }


# =========================================================
# Main Entity Resolver
# =========================================================

def resolve_entity(
    user_value: str,
    candidates: list[str],
    entity_type: str,
):
    """
    Resolve a user-provided entity without hardcoding catalog values.

    Resolution order:
        1. Exact DB candidate
        2. Explicit abbreviation from abbreviations.json
        3. Unique prefix / half-word against DB candidates
        4. Unique partial match against DB candidates
        5. Fuzzy typo/short-form match against DB candidates
        6. Not found

    The function keeps the existing resolve_entity() interface so the
    current ConversationManager/entity pipeline can continue calling it.
    """
    if not user_value:
        return {
            "status": "empty",
            "input": user_value,
            "entity_type": entity_type,
            "matched_value": None,
            "confidence": 0,
        }

    if not candidates:
        return {
            "status": "no_candidates",
            "input": user_value,
            "entity_type": entity_type,
            "matched_value": None,
            "confidence": 0,
        }

    # -------------------------------------------------
    # STEP 1 — Exact DB candidate
    # -------------------------------------------------

    result = exact_match(user_value, candidates)

    if result:
        return {
            "status": "resolved",
            "input": user_value,
            "entity_type": entity_type,
            **result,
        }

    # -------------------------------------------------
    # STEP 2 — Explicit abbreviation
    # -------------------------------------------------

    result = abbreviation_match(
        user_value,
        candidates,
        entity_type,
    )

    if result:
        return {
            "status": "resolved",
            "input": user_value,
            "entity_type": entity_type,
            **result,
        }

    # -------------------------------------------------
    # STEP 3 — Known spelling variant
    # -------------------------------------------------

    result = spelling_variant_match(
        user_value,
        candidates,
        entity_type,
    )

    if result:
        return {
            "status": "resolved",
            "input": user_value,
            "entity_type": entity_type,
            **result,
        }

    # -------------------------------------------------
    # STEP 4 — Unique prefix / half-word
    # -------------------------------------------------
    # -------------------------------------------------
    # STEP 3 — Unique prefix / half-word
    # -------------------------------------------------

    result = prefix_match(
        user_value,
        candidates,
    )

    if result:
        if result["method"] == "ambiguous":
            return {
                "status": "needs_confirmation",
                "input": user_value,
                "entity_type": entity_type,
                **result,
            }

        return {
            "status": "resolved",
            "input": user_value,
            "entity_type": entity_type,
            **result,
        }

    # -------------------------------------------------
    # STEP 4 — Partial / half-name
    # -------------------------------------------------

    result = partial_match(
        user_value,
        candidates,
    )

    if result:
        if result["method"] == "ambiguous":
            return {
                "status": "needs_confirmation",
                "input": user_value,
                "entity_type": entity_type,
                **result,
            }

        return {
            "status": "resolved",
            "input": user_value,
            "entity_type": entity_type,
            **result,
        }

    # -------------------------------------------------
    # STEP 5 — Fuzzy typo / natural short form
    # -------------------------------------------------

    result = fuzzy_match(
        user_value,
        candidates,
        score_cutoff=70,
    )

    if result:
        if result["method"] == "ambiguous":
            return {
                "status": "needs_confirmation",
                "input": user_value,
                "entity_type": entity_type,
                **result,
            }

        confidence = result["confidence"]

        if confidence >= 85:
            status = "resolved"
        elif confidence >= 75:
            status = "needs_confirmation"
        else:
            status = "not_found"

        return {
            "status": status,
            "input": user_value,
            "entity_type": entity_type,
            **result,
        }

    # -------------------------------------------------
    # STEP 6 — Not Found
    # -------------------------------------------------

    return {
        "status": "not_found",
        "input": user_value,
        "entity_type": entity_type,
        "matched_value": None,
        "confidence": 0,
    }
