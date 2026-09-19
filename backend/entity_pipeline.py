from backend.normalization.entity_normalizer import resolve_entity
from backend.database.frontend_mapping import FrontendMapper

def _find_value_across_fields(
    user_value,
    candidates,
    preferred_field=None
):
    """
    Search a user value across all available
    database fields.

    This is database-aware entity resolution.

    The AI may classify a value into the wrong field.
    Therefore, the actual database candidates are
    used to determine where the value belongs.
    """

    if not user_value:
        return None

    candidates = candidates or {}
 
    # ---------------------------------------------------------
    # 1. Try the field suggested by Qwen first
    # ---------------------------------------------------------

    fields_to_check = []

    if preferred_field and preferred_field in candidates:
        fields_to_check.append(preferred_field)

    # ---------------------------------------------------------
    # 2. Then check every other searchable field
    # ---------------------------------------------------------

    for field in candidates:

        if field not in fields_to_check:
            fields_to_check.append(field)

    resolved_matches = []

    # ---------------------------------------------------------
    # 3. Search value in each field
    # ---------------------------------------------------------

    for field in fields_to_check:

        field_candidates = candidates.get(field, [])

        if not field_candidates:
            continue

        result = resolve_entity(
            user_value=user_value,
            candidates=field_candidates,
            entity_type=field
        )

        if result.get("status") == "resolved":

            resolved_matches.append({
                "field": field,
                "result": result
            })

    # ---------------------------------------------------------
    # No match anywhere
    # ---------------------------------------------------------

    if not resolved_matches:
        return None

    # ---------------------------------------------------------
    # Exact / high-confidence match priority
    # ---------------------------------------------------------

    resolved_matches.sort(
        key=lambda item: (
            item["result"].get("method") == "exact_match",
            item["result"].get("confidence", 0)
        ),
        reverse=True
    )

    best = resolved_matches[0]

    return {
        "field": best["field"],
        "result": best["result"],
        "all_matches": resolved_matches
    }

def _resolve_part_number_value(
    user_value,
    candidates
):
    """
    Resolve a user-supplied frontend Part Number.

    Frontend:
        Part Number
            ↓
        canonical field: fenner

    Resolution priority:
        1. Fenner
        2. PartNumber

    No catalog values are hardcoded.
    """

    if not user_value:
        return None

    candidates = candidates or {}

    # ---------------------------------------------------------
    # Get the canonical field represented by the frontend
    # label "Part Number".
    # ---------------------------------------------------------

    part_number_field = None

    for canonical_field, frontend_label in (
        FrontendMapper.FRONTEND_MAPPING.items()
    ):

        if (
            str(frontend_label).strip().lower()
            == "part number"
        ):

            part_number_field = canonical_field
            break

    if not part_number_field:
        return None

    # ---------------------------------------------------------
    # Part Number frontend field → Fenner
    # ---------------------------------------------------------

    primary_candidates = candidates.get(
        part_number_field,
        []
    )

    if primary_candidates:

        result = resolve_entity(
            user_value=user_value,
            candidates=primary_candidates,
            entity_type=part_number_field
        )

        if result.get("status") == "resolved":

            return {
                "field": part_number_field,
                "result": result
            }

    # ---------------------------------------------------------
    # If Fenner did not match, find the canonical field
    # represented by "Competitor PartNo".
    # ---------------------------------------------------------

    fallback_field = None

    for canonical_field, frontend_label in (
        FrontendMapper.FRONTEND_MAPPING.items()
    ):

        if (
            str(frontend_label).strip().lower()
            == "competitor partno"
        ):

            fallback_field = canonical_field
            break

    if not fallback_field:
        return None

    fallback_candidates = candidates.get(
        fallback_field,
        []
    )

    if fallback_candidates:

        result = resolve_entity(
            user_value=user_value,
            candidates=fallback_candidates,
            entity_type=fallback_field
        )

        if result.get("status") == "resolved":

            return {
                "field": fallback_field,
                "result": result
            }

    return None 
    
    
    
def discover_missing_entities(
    user_message,
    extracted_data,
    database_layer
):
    """
    Discover catalog values that Qwen may have missed.

    Qwen is the primary semantic extractor.

    Database discovery is a supporting layer:
    - If Qwen already identified one or more fields,
      discovery is restricted to those fields.
    - If Qwen identified nothing, discovery can use all
      searchable fields as a fallback.
    - Existing spelling, partial-word and abbreviation
      resolution remains available through DB discovery.
    """

    if not user_message:
        return extracted_data or {}

    if not database_layer:
        return extracted_data or {}

    extracted_data = extracted_data or {}

    # ---------------------------------------------------------
    # IMPORTANT
    # Qwen already identified fields.
    #
    # Pass those fields to DB discovery so discovery does not
    # independently create unrelated fields from conversational
    # words in the user's sentence.
    # ---------------------------------------------------------

    preferred_fields = list(extracted_data.keys())

    try:

        discovered = database_layer.discover_entities_from_text(
            user_message,
            preferred_fields=preferred_fields
        )

    except Exception:

        # Backward compatibility:
        # If the database layer does not yet support
        # preferred_fields, keep the existing behavior.
        try:
            discovered = database_layer.discover_entities_from_text(
                user_message
            )
        except Exception:
            return extracted_data

    if not discovered:
        return extracted_data

    for field, discovery in discovered.items():

        if discovery is None:
            continue

        # DatabaseLayer returns:
        #
        # {
        #     "value": "...",
        #     "confidence": ...,
        #     "method": "..."
        # }

        if isinstance(discovery, dict):
            value = discovery.get("value")
        else:
            value = discovery

        if value is None:
            continue

        if isinstance(value, str) and not value.strip():
            continue

        # -----------------------------------------------------
        # Qwen is already the semantic extractor.
        #
        # Never overwrite a field already extracted by Qwen.
        # -----------------------------------------------------

        if field in extracted_data:
            continue

        extracted_data[field] = value

    return extracted_data
def resolve_extracted_entities(
    extracted_data,
    candidates
):
    """
    Resolve extracted entities against the actual
    database candidate values.

    Important:

    Qwen's extracted field is treated as a suggestion,
    not as absolute truth.

    If Qwen says:

        {"oem": "Escape"}

    but Escape exists in the model field and not
    in the OEM field, the database evidence wins.
    """

    resolved_data = {}
    resolution_details = {}

    if not extracted_data:
        return {
            "resolved_data": {},
            "resolution_details": {}
        }

    candidates = candidates or {}

    # ---------------------------------------------------------
    # Process every value extracted by Qwen
    # ---------------------------------------------------------

    for extracted_field, user_value in extracted_data.items():

        if user_value is None:
            continue

        if isinstance(user_value, str):

            user_value = user_value.strip()

            if not user_value:
                continue

        # -----------------------------------------------------
        # Database-aware resolution
        # -----------------------------------------------------
        if extracted_field == "part_number":

            match = _resolve_part_number_value(
                user_value=user_value,
                candidates=candidates
            )

        else:

            match = _find_value_across_fields(
                user_value=user_value,
                candidates=candidates,
                preferred_field=extracted_field
            )
            
        # -----------------------------------------------------
        # No database match
        # -----------------------------------------------------

        if match is None:

            # Keep Qwen's original field/value.
            #
            # This is important for values that may not
            # currently exist in the database.

            resolved_data[extracted_field] = user_value

            resolution_details[extracted_field] = {
                "status": "not_resolved",
                "input": user_value,
                "original_field": extracted_field,
                "matched_field": None,
                "matched_value": None,
                "confidence": 0
            }

            continue

        # -----------------------------------------------------
        # Database identified the actual field
        # -----------------------------------------------------

        matched_field = match["field"]
        result = match["result"]

        matched_value = result.get(
            "matched_value"
        )

        # -----------------------------------------------------
        # Store using the database-confirmed field
        # -----------------------------------------------------

        resolved_data[matched_field] = matched_value

        resolution_details[extracted_field] = {
            "status": "resolved",
            "input": user_value,
            "original_field": extracted_field,
            "matched_field": matched_field,
            "matched_value": matched_value,
            "confidence": result.get(
                "confidence",
                0
            ),
            "method": result.get(
                "method"
            )
        }

    return {
        "resolved_data": resolved_data,
        "resolution_details": resolution_details
    }