from typing import Optional
from models.user import User


class Event():
    def __init__(self, id: int, title: str,
                 description: str, creator: User,
                 image: Optional[str] = None) -> None:
        self.id = id
        self.title = title
        self.image = image
        self.description = description
        self.creator = creator

    def __str__(self) -> str:
        result = (f"id: {self.id} \n"
                  f"title: {self.title} \n"
                  f"creator: {self.creator.email}")

        return result
