"""Contract chart giua chatbot backend va frontend."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

CHART_SCHEMA_VERSION = 1
ChartType = Literal["bar", "line", "pie", "donut", "stacked_bar", "area"]
MAX_CATEGORIES = 12
MAX_SERIES = 6
MAX_CHARTS = 4


class ChartSeries(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    data: list[float] = Field(..., min_length=1)


class ChartSpec(BaseModel):
    chart_type: ChartType
    title: str = Field(..., min_length=1, max_length=200)
    categories: list[str] = Field(..., min_length=1, max_length=MAX_CATEGORIES)
    series: list[ChartSeries] = Field(..., min_length=1, max_length=MAX_SERIES)
    unit: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def check_shape(self) -> "ChartSpec":
        category_count = len(self.categories)
        for series in self.series:
            if len(series.data) != category_count:
                raise ValueError(
                    f"series '{series.name}' co {len(series.data)} diem du lieu "
                    f"nhung co {category_count} categories."
                )
        if self.chart_type in ("pie", "donut") and len(self.series) != 1:
            raise ValueError("pie/donut chi nhan dung 1 series.")
        return self


class ChartDecision(BaseModel):
    has_chart: bool = Field(description="False neu du lieu khong du de ve bieu do.")
    charts: list[ChartSpec] = Field(default_factory=list, max_length=MAX_CHARTS)

    @model_validator(mode="after")
    def check_charts(self) -> "ChartDecision":
        if self.has_chart and not self.charts:
            raise ValueError("has_chart=True phai co it nhat mot chart.")
        if not self.has_chart and self.charts:
            raise ValueError("has_chart=False khong duoc kem charts.")
        return self


class ChartPayload(BaseModel):
    schema_version: int = CHART_SCHEMA_VERSION
    spec: ChartSpec
