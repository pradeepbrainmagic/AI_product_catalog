from ollama import chat
import json

MODEL_NAME = "qwen2.5:7b"

class QwenCatalogEngine:
    """
    Generic Product Catalog Query Understanding Engine.

    This engine does NOT contain dataset-specific fields.

    It receives the available canonical fields dynamically
    from the database/schema layer and extracts values from
    the user's message.
    """

    def __init__(self, model_name=MODEL_NAME):
        self.model_name = model_name

    # ---------------------------------------------------------
    # BUILD SYSTEM PROMPT
    # ---------------------------------------------------------

    def _build_system_prompt(self, available_fields):
        fields_text = "\n".join(
            f"- {field}"
            for field in available_fields
        )

        return f"""
    You are a Generic Product Catalog Query Understanding AI.

    Your job is to understand the user's complete message and
    extract ONLY the product-catalog information that the user
    actually provides.

    The database schema is dynamic.

    You MUST NOT assume a fixed catalog structure.

    The currently available canonical fields are:

    {fields_text}

    IMPORTANT PRINCIPLE:

    First understand the meaning of the COMPLETE user message.

    Then identify which words or phrases are actual catalog
    information supplied by the user.

    Do NOT treat every word in the user's message as a catalog value.

    Users may communicate in ANY natural language style.
    They may use:
    - a single value
    - multiple values
    - short phrases
    - complete sentences
    - conversational sentences
    - abbreviations
    - spelling mistakes
    - partial words
    - informal wording
    - mixed information and conversational wording

    Your job is to understand the user's intent and extract
    only the actual catalog information.

    RULES:

    1. Extract only values that the user explicitly provides
    or clearly specifies as catalog information.

    2. Do NOT invent, assume, predict, or complete missing
    catalog information.

    3. Do NOT extract a field merely because a word in the
    sentence is semantically related to that field.

    4. Conversational, descriptive, request, or intent-related
    wording is NOT automatically a catalog value.

    5. A word or phrase should be assigned to a catalog field
    only when the complete context indicates that the user
    is actually providing that information.

    6. If the user provides a complete catalog value inside
    a longer natural-language sentence, extract the COMPLETE
    value, not just one word from it.

    7. If a catalog value contains multiple words, preserve the
    complete value exactly as provided by the user.

    8. Do NOT split a multi-word catalog value into unrelated
    fields.

    9. If multiple catalog values are clearly provided in the
    same message, extract all of them.

    10. Do NOT infer relationships between values that the user
        did not explicitly provide.

    11. Do NOT assume OEM, model, engine, year, product,
        category, part number, or any other field from another
        value.

    12. If the user gives only one piece of information, extract
        only that information.

    13. If the user gives a year, extract it as a year only.
        Do not interpret part of the year as another value.

    14. If the user gives an OEM, model, product, engine,
        category, part number, or other catalog value, identify
        the appropriate canonical field only when the message
        provides enough context to do so.

    15. Do NOT create a catalog value from ordinary conversational
        wording simply because that wording resembles a database
        value.

    16. If a word is ambiguous between conversational wording and
        a catalog value, do NOT guess. Prefer extracting it only
        when the user's sentence clearly indicates that it is
        being supplied as catalog information.

    17. Understand spelling mistakes and abbreviations.

    18. Do NOT unnecessarily correct or rewrite the user's value.
        Preserve the user's supplied value so that the downstream
        entity-resolution layer can resolve spelling mistakes,
        abbreviations, and variants.

    19. Short messages are valid catalog queries.

    Examples of short messages:

    BMW
    Pulsar
    ABS
    2023
    K060434

    20. Natural-language sentences are also valid catalog queries.

    21. Do NOT ask questions.

    22. Do NOT search the database.

    23. Do NOT generate explanations.

    24. Return ONLY valid JSON.

    25. Use ONLY the exact canonical field names provided below:

    {fields_text}

    26. Do not create fields that are not present in the
        available canonical fields.

    27. Do not output empty, null, guessed, or inferred values.
    
    28. When multiple words or phrases in a natural-language message
    appear to be catalog values, identify each value according to
    its most appropriate canonical field based on the complete
    message context.

    Do not assume that a catalog value must be preceded by an
    explicit field label such as "OEM", "model", "year", or
    "category".

    If a value is clearly recognizable as a catalog value from
    its meaning and context, extract it using the appropriate
    canonical field.

    If a word is ordinary conversational wording and there is
    insufficient evidence that it is a catalog value, do not
    extract it.
    
    29. The output format MUST be:

    {{
        "extracted_data": {{
            "field_name": "value"
        }}
    }}

    If no catalog information can be confidently identified,
    return:

    {{
        "extracted_data": {{}}
    }}

    IMPORTANT:

    The goal is NOT to extract every meaningful word.

    The goal is to extract only the information that the user
    is actually providing for product-catalog lookup.

    Understand the whole sentence first.
    Extract the catalog information second.
    Never hallucinate missing catalog information.

    Example 1:

    Available fields:
    - oem
    - model
    - engine
    - year
    - product
    - part_number

    User:
    "Volkswagen Passat 2022"

    Output:
    {{
        "extracted_data": {{
            "oem": "Volkswagen",
            "model": "Passat",
            "year": "2022"
        }}
    }}

    Example 2:

    Available fields:
    - oem
    - model
    - engine
    - year
    - product
    - part_number

    User:
    "2021"

    Output:
    {{
        "extracted_data": {{
            "year": "2021"
        }}
    }}

    Example 3:

    Available fields:
    - oem
    - model
    - engine
    - year
    - product
    - part_number

    User:
    "I need information for year 2021"

    Output:
    {{
        "extracted_data": {{
            "year": "2021"
        }}
    }}

    Example 4:

    Available fields:
    - oem
    - model
    - engine
    - year
    - product
    - part_number

    User:
    "Freightliner"

    Output:
    {{
        "extracted_data": {{
            "oem": "Freightliner"
        }}
    }}

    Example 5:

    Available fields:
    - oem
    - model
    - engine
    - year
    - product
    - part_number

    User:
    "Cherokee"

    Output:
    {{
        "extracted_data": {{
            "model": "Cherokee"
        }}
    }}

    Example 6:

    Available fields:
    - oem
    - model
    - engine
    - year
    - product
    - part_number

    User:
    "6-Cyl. 4.0 L"

    Output:
    {{
        "extracted_data": {{
            "engine": "6-Cyl. 4.0 L"
        }}
    }}

    Example 7:

    Available fields:
    - oem
    - model
    - engine
    - year
    - product
    - part_number

    User:
    "Volkswagen Passat"

    Output:
    {{
        "extracted_data": {{
            "oem": "Volkswagen",
            "model": "Passat"
        }}
    }}

    Example 8:

    Available fields:
    - oem
    - model
    - engine
    - year
    - product
    - part_number

    User:
    "K060434"

    Output:
    {{
        "extracted_data": {{
            "part_number": "K060434"
        }}
    }}
    
    Example 9:

    Available fields:
    - oem
    - model
    - engine
    - year
    - product
    - category
    - part_number

    User:
    "Passenger Car Frod"

    Output:
    {{
        "extracted_data": {{
            "category": "Passenger Car",
            "oem": "Frod"
        }}
    }}

    Do not add any field that is not clearly provided by the
    user.

    Return ONLY JSON.
    """

    # ---------------------------------------------------------
    # EXTRACT USER QUERY
    # ---------------------------------------------------------

    def extract(self, user_message, available_fields):
        """
        Extract catalog entities dynamically.

        Parameters
        ----------
        user_message : str
            User's latest message.

        available_fields : list
            Canonical fields supported by the current dataset.

        Returns
        -------
        dict
            Dynamic extracted data.
        """

        if not isinstance(available_fields, list):
            raise ValueError(
                "available_fields must be a list"
            )

        if not user_message or not user_message.strip():
            return {
                "extracted_data": {}
            }

        system_prompt = self._build_system_prompt(
            available_fields
        )

        response = chat(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message.strip()
                }
            ],
            format="json",
            options={
                "temperature": 0
            }
        )

        try:
            result = json.loads(
                response.message.content
            )
        except json.JSONDecodeError:
            return {
                "extracted_data": {}
            }

        extracted_data = result.get(
            "extracted_data",
            {}
        )

        if not isinstance(extracted_data, dict):
            extracted_data = {}

        # -----------------------------------------------------
        # SAFETY FILTER
        # -----------------------------------------------------
        # Qwen accidentally creates a field that doesn't
        # exist in the current dataset → remove it.
        # -----------------------------------------------------

        valid_fields = set(
            available_fields
        )

        filtered_data = {
            key: value
            for key, value in extracted_data.items()
            if key in valid_fields
            and value is not None
            and str(value).strip() != ""
        }

        return {
            "extracted_data": filtered_data
        }
        
        
        
    def understand_initial_message(self, user_message):
        """
        Understand whether the initial user message is:
        - GREETING_ONLY
        - CATALOG_QUERY

        This method does NOT perform catalog extraction.
        Existing extract() remains unchanged.
        """

        if not user_message or not user_message.strip():
            return {
                "intent": "CATALOG_QUERY",
                "greeting_response": ""
            }

        system_prompt = """
    You are the conversation understanding layer of an AI Product Catalog Assistant.

    Understand the user's message based on its meaning, not by matching a fixed
    list of greeting words.

    Your task is to determine whether the user's message is:

    1. GREETING_ONLY
    The user is only greeting or starting a casual conversation and has not
    provided any product/catalog request.

    2. CATALOG_QUERY
    The user has provided or requested any catalog/product/vehicle information,
    even if the message also contains a greeting.

    IMPORTANT:

    - Understand natural language semantically.
    - Do NOT depend on a hardcoded list of greeting words.
    - A greeting combined with catalog information is NOT GREETING_ONLY.
    - For example:
        "Hello AI, I want to know about Ford"
        "Good morning, show me BMW parts"
        "Hey, I need a brake pad for Ford"

    These are CATALOG_QUERY messages.

    - A message such as:
        "Hello AI"
        "Hey there"
        "Good morning"
        "Nice to meet you"

    may be GREETING_ONLY if there is no catalog request.

    - Understand unfamiliar or naturally written greetings from their meaning.
    - Do not invent catalog information.

    For GREETING_ONLY:
    Generate a short, natural conversational response.

    For CATALOG_QUERY:
    Do NOT generate a response. The existing catalog processing flow
    will handle the request.

    IMPORTANT ABOUT SELF-REFERENCE:

    When generating a greeting response:
    - Refer to yourself only as "I", "me", or "my".
    - NEVER use "we", "us", or "our" to refer to yourself.

    The response should feel like a natural AI assistant, not a fixed template.

    Return ONLY valid JSON in this format:

    {
        "intent": "GREETING_ONLY",
        "greeting_response": "Natural response here"
    }

    OR

    {
        "intent": "CATALOG_QUERY",
        "greeting_response": ""
    }
    """

        try:
            from ollama import chat

            response = chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_message.strip()
                    }
                ],
                format="json",
                options={
                    "temperature": 0.4
                }
            )

            import json

            result = json.loads(
                response.message.content
            )

            intent = result.get(
                "intent",
                "CATALOG_QUERY"
            )

            if intent not in {
                "GREETING_ONLY",
                "CATALOG_QUERY"
            }:
                intent = "CATALOG_QUERY"

            greeting_response = result.get(
                "greeting_response",
                ""
            )

            if not isinstance(
                greeting_response,
                str
            ):
                greeting_response = ""

            return {
                "intent": intent,
                "greeting_response": greeting_response.strip()
            }

        except Exception as e:

            print(
                "DEBUG INITIAL MESSAGE UNDERSTANDING ERROR:",
                e
            )

            # IMPORTANT:
            # If understanding fails, continue with the
            # existing catalog flow rather than breaking it.
            return {
                "intent": "CATALOG_QUERY",
                "greeting_response": ""
            }

    # ---------------------------------------------------------
    # GENERATE DISPLAY FORMAT QUESTION
    # ---------------------------------------------------------

    def generate_display_format_question(
        self,
        records_count,
        conversation_context=None
    ):
        """
        Generate a natural conversational question asking
        the user whether product details should be displayed
        as cards or as a table.

        This does NOT affect catalog reasoning or questioning.
        """

        context_text = ""

        if conversation_context:
            context_text = str(
                conversation_context
            )

        system_prompt = """
You are an AI Product Catalog Assistant.

The product catalog search has completed and matching
product records are ready to be shown to the user.

Ask the user naturally whether they would like to see
the product details in Card format or Table format.

IMPORTANT:

- Respond naturally like a conversational AI assistant.
- Do NOT use a fixed response template.
- Do NOT repeatedly use the same sentence structure.
- Use the available conversation context when useful.
- Keep the message short and clear.
- Mention that both Card and Table formats are available.
- Do not invent product information.
- Do not discuss internal processing, database logic,
  extraction, or backend details.
- Do not ask about OEM, model, engine, year, product,
  category, or part number.
- This is ONLY a display-format preference question.

IMPORTANT ABOUT SELF-REFERENCE:

- Refer to yourself only as I, me, or my.
- NEVER use we, us, or our to refer to yourself.

The user will receive two selectable options:

Card
Table

Return ONLY the natural question/message text.
"""

        user_prompt = f"""
Matching product count: {records_count}

Conversation context:
{context_text}

Generate a natural message asking the user whether
they would like the product details displayed as cards
or in a table.
"""

        try:

            response = chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                options={
                    "temperature": 0.5
                }
            )

            message = (
                response.message.content
                .strip()
            )

            if message:
                return message

        except Exception as e:

            print(
                "DEBUG DISPLAY FORMAT QUESTION ERROR:",
                e
            )

        return (
            "How would you like me to display "
            "the product details — as cards or in a table?"
        )
# -------------------------------------------------------------
# SINGLE ENGINE INSTANCE
# -------------------------------------------------------------

qwen_engine = QwenCatalogEngine()


# -------------------------------------------------------------
# BACKWARD-FRIENDLY FUNCTION
# -------------------------------------------------------------

def extract_catalog_query(
    user_message,
    available_fields
):
    """
    Generic wrapper used by ConversationManager.
    """

    return qwen_engine.extract(
        user_message=user_message,
        available_fields=available_fields
    )
    
def understand_initial_message(
    user_message
):
    """
    Generic wrapper used by ConversationManager
    for initial conversation understanding.

    Uses the existing Qwen engine instance.
    """

    return qwen_engine.understand_initial_message(
        user_message=user_message
    )
    
def generate_display_format_question(
    records_count,
    conversation_context=None
):
    """
    Generate a natural Card/Table display question.
    """

    return qwen_engine.generate_display_format_question(
        records_count=records_count,
        conversation_context=conversation_context
    )