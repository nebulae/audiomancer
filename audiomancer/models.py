from pydantic import BaseModel
from typing import List

class Segment(BaseModel):
    text: str
    approx_words: int

class Section(BaseModel):
    title: str
    segments: List[Segment]

class Chapter(BaseModel):
    title: str
    sections: List[Section]

class TextResponse(BaseModel):
    chapters: List[Chapter]


class ReadingNote(BaseModel):
    citation: str
    argument: str
    main_points: List[str]
    evidence: List[str]
    assessment: str
