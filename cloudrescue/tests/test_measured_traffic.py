import asyncio
from pathlib import Path

import pytest
from cloudrescue_traces import Frame, load

from tools.measured_traffic import measure, summarize

EXAMPLES = Path("packages/reliability-traces/examples")


def test_portable_trace_examples_normalize_identically():
    assert load(EXAMPLES / "trace.csv") == load(EXAMPLES / "trace.json")
    assert load(EXAMPLES / "trace.json")[0] == Frame(0, 3, "healthy")


@pytest.mark.parametrize(
    "body",
    [
        '[{"time_ms":0,"requests":3,"fault":"healthy","url":"http://example.com"}]',
        '[{"time_ms":0,"requests":3,"requests":4,"fault":"healthy"}]',
        '[{"time_ms":0,"requests":999,"fault":"healthy"}]',
        '[{"time_ms":false,"requests":1,"fault":"healthy"}]',
    ],
)
def test_trace_rejects_invalid_rows(tmp_path, body):
    path = tmp_path / "trace.json"
    path.write_text(body)
    with pytest.raises(ValueError):
        load(path)


def test_measured_http_detects_error_and_recovery():
    result = asyncio.run(
        measure(
            [
                Frame(0, 1, "healthy"),
                Frame(1000, 1, "error"),
                Frame(2000, 1, "healthy"),
            ],
            42,
            "baseline",
        )
    )
    assert result["request_success"] == pytest.approx(2 / 3)
    assert result["first_impaired_second"] == 1
    assert result["recovered_second"] == 2
    assert result["series"][1]["responses"][0]["status"] == 500


def test_summary_keeps_paired_bias_and_excludes_zero_percentage_denominator():
    rows = [
        {"modeled": {"x": 2}, "measured": {"x": 0}},
        {"modeled": {"x": 1}, "measured": {"x": 2}},
    ]
    result = summarize(rows, "x")
    assert result["bias"] == 0.5
    assert result["mean_absolute_error"] == 1.5
    assert result["mean_absolute_percentage_error"] == 50
    assert result["percentage_samples"] == 1
