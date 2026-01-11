class ApiValidationException(Exception):
    """
    Exception raised for API validation errors.
    """

    def __init__(self, code: list[str], description: str, status_code: int = 400):
        self.status_code = status_code
        self.code = code
        self.description = description

    def __str__(self):
        return (
            f"ApiValidationException(code={self.code}, description={self.description})"
        )
