from pathlib import Path
import json

from backend.normalization.entity_normalizer import resolve_entity


# =========================================================
# FILES
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

SPELLING_VARIANTS_FILE = (
    BASE_DIR / "spelling_variants.json"
)

ABBREVIATIONS_FILE = (
    BASE_DIR / "abbreviations.json"
)


# =========================================================
# LOAD JSON
# =========================================================

def load_json_file(file_path):

    try:

        with file_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            f"\nCould not load {file_path.name}: {error}"
        )

        return {}


spelling_data = load_json_file(
    SPELLING_VARIANTS_FILE
)

abbreviation_data = load_json_file(
    ABBREVIATIONS_FILE
)


SPELLING_FIELDS = (
    spelling_data.get("fields", {})
)

ABBREVIATION_FIELDS = (
    abbreviation_data.get("fields", {})
)


# =========================================================
# TEST HELPER
# =========================================================

def run_test(
    title,
    user_input,
    entity_type,
    candidates
):

    print("\n" + "=" * 70)

    print(title)

    print("Input      :", user_input)

    print("Entity     :", entity_type)

    print(
        "Candidates :",
        candidates[:10],
        "..."
        if len(candidates) > 10
        else ""
    )

    result = resolve_entity(
        user_value=user_input,
        candidates=candidates,
        entity_type=entity_type
    )

    print("Result     :", result)

    return result


# =========================================================
# GET CANONICAL VALUES FROM JSON
# =========================================================

def get_spelling_field_data(field):

    field_data = (
        SPELLING_FIELDS.get(
            field,
            {}
        )
    )

    if not isinstance(field_data, dict):

        return {}

    return field_data


def get_abbreviation_field_data(field):

    field_data = (
        ABBREVIATION_FIELDS.get(
            field,
            {}
        )
    )

    if not isinstance(field_data, dict):

        return {}

    return field_data


# =========================================================
# BUILD CANDIDATES FROM ACTUAL JSON DATA
# =========================================================

def build_candidates(field):

    candidates = []

    # -----------------------------------------------------
    # Canonical values from spelling_variants.json
    # -----------------------------------------------------

    spelling_variants = (
        get_spelling_field_data(field)
    )

    for variant, canonical in (
        spelling_variants.items()
    ):

        if canonical is None:
            continue

        canonical = str(
            canonical
        ).strip()

        if (
            canonical
            and canonical not in candidates
        ):

            candidates.append(
                canonical
            )

    # -----------------------------------------------------
    # Canonical values from abbreviations.json
    # -----------------------------------------------------

    abbreviations = (
        get_abbreviation_field_data(field)
    )

    for abbreviation, canonical in (
        abbreviations.items()
    ):

        if canonical is None:
            continue

        canonical = str(
            canonical
        ).strip()

        if (
            canonical
            and canonical not in candidates
        ):

            candidates.append(
                canonical
            )

    return candidates


# =========================================================
# TEST EXACT MATCH
# =========================================================

def test_exact_match(field):

    candidates = build_candidates(
        field
    )

    if not candidates:

        print(
            f"\nNo candidates available for {field}"
        )

        return

    canonical = candidates[0]

    run_test(
        f"EXACT {field.upper()}",
        canonical,
        field,
        candidates
    )


# =========================================================
# TEST SPELLING VARIANT
# =========================================================

def test_spelling_variant(field):

    variants = (
        get_spelling_field_data(field)
    )

    if not variants:

        print(
            f"\nNo spelling variants available for {field}"
        )

        return

    candidates = build_candidates(
        field
    )

    # -----------------------------------------------------
    # Find a variant whose canonical value exists
    # in the candidate list.
    # -----------------------------------------------------

    for variant, canonical in (
        variants.items()
    ):

        if canonical is None:
            continue

        canonical = str(
            canonical
        ).strip()

        if (
            variant
            and canonical in candidates
        ):

            result = run_test(
                f"SPELLING VARIANT {field.upper()}",
                variant,
                field,
                candidates
            )

            return result

    print(
        f"\nNo valid spelling variant found for {field}"
    )


# =========================================================
# TEST ABBREVIATION
# =========================================================

def test_abbreviation(field):

    abbreviations = (
        get_abbreviation_field_data(field)
    )

    if not abbreviations:

        print(
            f"\nNo abbreviations available for {field}"
        )

        return

    candidates = build_candidates(
        field
    )

    for abbreviation, canonical in (
        abbreviations.items()
    ):

        if canonical is None:
            continue

        canonical = str(
            canonical
        ).strip()

        if (
            abbreviation
            and canonical in candidates
        ):

            result = run_test(
                f"ABBREVIATION {field.upper()}",
                abbreviation,
                field,
                candidates
            )

            return result

    print(
        f"\nNo valid abbreviation found for {field}"
    )


# =========================================================
# RUN TESTS FOR ACTUAL DATASET FIELDS
# =========================================================

TEST_FIELDS = [
    "oem",
    "model",
    "engine",
    "year",
    "producttype",
    "category",
]


# =========================================================
# EXACT TESTS
# =========================================================

print("\n")
print("#" * 70)
print("EXACT MATCH TESTS")
print("#" * 70)

for field in TEST_FIELDS:

    test_exact_match(field)


# =========================================================
# SPELLING VARIANT TESTS
# =========================================================

print("\n")
print("#" * 70)
print("SPELLING VARIANT TESTS")
print("#" * 70)

for field in TEST_FIELDS:

    test_spelling_variant(field)


# =========================================================
# ABBREVIATION TESTS
# =========================================================

print("\n")
print("#" * 70)
print("ABBREVIATION TESTS")
print("#" * 70)

for field in TEST_FIELDS:

    test_abbreviation(field)


# =========================================================
# MANUAL DYNAMIC TESTS
# =========================================================
#
# These use actual canonical values already present in the
# JSON files. No dataset-specific value is hardcoded here.
#
# =========================================================

print("\n")
print("#" * 70)
print("TEST SUMMARY")
print("#" * 70)

print(
    "Fields tested:",
    TEST_FIELDS
)

print(
    "Spelling JSON loaded:",
    bool(SPELLING_FIELDS)
)

print(
    "Abbreviation JSON loaded:",
    bool(ABBREVIATION_FIELDS)
)

print("\nAll dynamic entity-normalizer tests completed.")