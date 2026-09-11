"""Server-side pagination — "ne jamais renvoyer 32 000 joueurs au
navigateur" (docs/ui.md). Every list endpoint returns this shape.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

TAILLE_PAGE = 50


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    taille_page: int
    total: int


def paginer(elements: list[T], page: int) -> Page[T]:
    page = max(page, 1)
    debut = (page - 1) * TAILLE_PAGE
    return Page(items=elements[debut : debut + TAILLE_PAGE], page=page, taille_page=TAILLE_PAGE, total=len(elements))
