
import json
import subprocess

from scripts import run_pipeline


def test_pipeline_records_failure_and_returns_nonzero(monkeypatch, tmp_path):
    """A failed pipeline stage must be recorded and return exit code 1."""

    log_file = tmp_path / "pipeline_runs.jsonl"

    monkeypatch.setattr(run_pipeline, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(run_pipeline, "RUN_LOG", log_file)
    monkeypatch.setattr(
        run_pipeline.sys,
        "argv",
        ["run_pipeline.py", "--order-items", "10"],
    )

    def simulate_failure(command, cwd, check):
        raise subprocess.CalledProcessError(
            returncode=2,
            cmd=command,
        )

    monkeypatch.setattr(
        run_pipeline.subprocess,
        "run",
        simulate_failure,
    )

    result = run_pipeline.main()

    assert result == 1
    assert log_file.exists()

    record = json.loads(log_file.read_text(encoding="utf-8"))

    assert record["status"] == "FAILED"
    assert "CalledProcessError" in record["failure_reason"]
    assert "ended_at_utc" in record
    assert record["total_duration_seconds"] >= 0
    assert record["run_id"]
