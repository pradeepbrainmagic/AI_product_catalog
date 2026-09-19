class ConversationState:
    """
    Generic conversation state.

    Fields are discovered dynamically from the database schema.
    No dataset-specific fields are defined here.
    """

    def __init__(self, available_fields=None):
        self.available_fields = list(
            available_fields or []
        )

        self.data = {
            field: None
            for field in self.available_fields
        }

    def update(self, extracted_data):
        if not extracted_data:
            return self.data

        for field, value in extracted_data.items():

            if field not in self.data:
                continue

            if value is None:
                continue

            if isinstance(value, str) and not value.strip():
                continue

            self.data[field] = value

        return self.data

    def get(self, field):
        return self.data.get(field)

    def get_all(self):
        return self.data.copy()

    def missing_fields(self):
        return [
            field
            for field in self.available_fields
            if self.data.get(field) is None
        ]

    def has(self, field):
        value = self.data.get(field)

        return (
            value is not None
            and not (
                isinstance(value, str)
                and not value.strip()
            )
        )

    def reset(self):
        for field in self.available_fields:
            self.data[field] = None

    def __repr__(self):
        return f"ConversationState({self.data})"