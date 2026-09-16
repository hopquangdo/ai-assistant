from pydantic import BaseModel, Field


class Suggestion(BaseModel):
	question: str = Field(description="Một câu hỏi gợi ý, tiếng Việt, dưới 15 từ")

__all__ = ["Suggestion"]
