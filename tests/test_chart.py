import pytest
from pydantic import ValidationError

from src.agents.nodes.react.prompt import SELECT_PROMPT
from src.agents.nodes.genchart.prompt import CHART_PROMPT
from src.schemas.chart import ChartDecision, ChartSeries, ChartSpec
from src.utils.text import load_prompt


def valid_spec(**overrides):
    values = {
        "chart_type": "bar",
        "title": "So sanh",
        "categories": ["A", "B"],
        "series": [{"name": "Gia tri", "data": [1, 2]}],
    }
    values.update(overrides)
    return ChartSpec(**values)


def test_chart_spec_accepts_valid_shape():
    spec = valid_spec()
    assert spec.series[0].data == [1.0, 2.0]


def test_chart_spec_rejects_mismatched_series_length():
    with pytest.raises(ValidationError, match="diem du lieu"):
        valid_spec(series=[ChartSeries(name="Gia tri", data=[1])])


def test_chart_spec_rejects_multiple_pie_series():
    with pytest.raises(ValidationError, match="pie/donut"):
        valid_spec(
            chart_type="pie",
            series=[
                {"name": "A", "data": [1, 2]},
                {"name": "B", "data": [3, 4]},
            ],
        )


def test_chart_spec_rejects_too_many_categories():
    with pytest.raises(ValidationError):
        valid_spec(categories=[str(i) for i in range(13)], series=[{"name": "S", "data": list(range(13))}])


def test_chart_decision_without_charts_is_valid():
    decision = ChartDecision(has_chart=False)
    assert decision.charts == []


def test_chart_decision_accepts_multiple_charts():
    decision = ChartDecision(has_chart=True, charts=[valid_spec(), valid_spec(title="Xếp hạng")])
    assert len(decision.charts) == 2


def test_load_prompt_prefers_markdown():
    assert load_prompt("select") == SELECT_PROMPT
    assert load_prompt("chart") == CHART_PROMPT


