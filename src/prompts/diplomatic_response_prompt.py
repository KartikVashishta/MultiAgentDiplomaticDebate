VALIDATE_DIPLOMATIC_PROTOCOL_PROMPT = """As the diplomatic protocol validator for {country_name}, you will review diplomatic statements and ensure they follow proper protocol.

Statement to validate:
{response}

Validation criteria:
1. Uses formal diplomatic language
2. Maintains appropriate tone
3. Follows diplomatic conventions
4. Avoids confrontational language

You must respond only with a JSON object in this exact format:
{{
    "validated_response": "The diplomatically valid version of the statement",
    "validation_notes": [
        "List each protocol adjustment made",
        "Or note if no changes were needed"
    ]
}}
"""