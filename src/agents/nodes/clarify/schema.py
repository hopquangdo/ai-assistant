from pydantic import BaseModel, Field


class ClarifyDecision(BaseModel):
    needs_clarification: bool = Field(
        default=False,
        description="True only when a required value is missing and no valid default exists."
    )
    reply: str = Field(
        default="",
        description="User-facing Vietnamese text: clarification question or casual reply. Empty for business questions."
    )
    needs_react: bool = Field(
        default=True,
        description="True when the question needs business tools; false for casual conversation."
    )


__all__ = ["ClarifyDecision"]
