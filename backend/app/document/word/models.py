from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional


class ParagraphBlock(BaseModel):
    index: int
    text: str
    style: Optional[str] = None


class TableCell(BaseModel):
    row: int
    col: int
    text: str


class TableBlock(BaseModel):
    table_index: int
    rows: List[List[str]]


class DocumentStructure(BaseModel):
    paragraphs: List[ParagraphBlock]
    tables: List[TableBlock]