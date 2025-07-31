class User:
    def __init__(self, id: int, email: str) -> None:
        self.id = id
        self.email = email

    def __str__(self) -> str:
        return f"id: {self.id}, email: {self.email}"
