from pydantic import BaseModel, Field


class ResponseOutput(BaseModel):
    answer: str = Field(
        description="Final answer shown to the user."
    )

    should_generate_chart: bool = Field(
        default=False,
        description="Whether the answer should be visualized as a chart."
    )
    
__all__ = ["ResponseOutput"]
