#!/usr/bin/env python3
"""
Test script for the dummy metric collector.

This script creates sample metrics files and tests the collector's functionality.
"""

import json
import tempfile
import subprocess
import sys
from pathlib import Path
from typing import List
import shutil


def create_sample_data_files(base_dir: Path) -> List[Path]:
    """Create sample *_data.json files for testing."""

    # Create directory structure with data files
    sample_data = [
        {
            "path": "dataset1/method1/D1_data.json",
            "data": {"result": 10.5, "error": None},
        },
        {
            "path": "dataset1/method2/D1_data.json",
            "data": {"result": 15.2, "error": None},
        },
        {
            "path": "dataset2/method1/D2_data.json",
            "data": {"result": 8.7, "error": None},
        },
        {
            "path": "dataset2/method2/D2_data.json",
            "data": {"result": 12.1, "error": None},
        },
        {
            "path": "dataset3/method1/D3_data.json",
            "data": {"result": 20.0, "error": None},
        },
        {
            "path": "dataset3/method2/D3_data.json",
            "data": {"result": "invalid", "error": "computation failed"},
        },
    ]

    created_files = []

    for item in sample_data:
        file_path = base_dir / item["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as f:
            json.dump(item["data"], f, indent=2)

        created_files.append(file_path)
        print(f"Created: {file_path}")

    return created_files


def run_collector_test(
    collector_script: Path, input_dir: Path, output_dir: Path, **kwargs
):
    """Run the collector with given parameters."""

    cmd = [
        sys.executable,
        str(collector_script),
        "--input-pattern",
        str(input_dir / "**" / "*_data.json"),
        "--output_dir",
        str(output_dir),
    ]

    # Add additional arguments
    for key, value in kwargs.items():
        if isinstance(value, bool) and value:
            cmd.append(f"--{key.replace('_', '-')}")
        elif value is not None:
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    print(f"\n=== Running collector ===")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    print(f"Return code: {result.returncode}")
    print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")

    return result


def verify_output(output_dir: Path, expected_values: list):
    """Verify the collector output."""

    # Check if metrics.json was created
    metrics_file = output_dir / "metrics.json"
    cli_file = output_dir / "cli.txt"

    assert metrics_file.exists(), f"metrics.json not found in {output_dir}"
    assert cli_file.exists(), f"cli.txt not found in {output_dir}"

    # Load and verify metrics
    with open(metrics_file, "r") as f:
        metrics = json.load(f)

    print(f"\n=== Results Output ===")
    print(json.dumps(metrics, indent=2))

    # Basic verification
    assert "count" in metrics, "Count not found in metrics"
    assert "values" in metrics, "Values not found in metrics"
    assert metrics["count"] == len(expected_values), (
        f"Expected {len(expected_values)} values, got {metrics['count']}"
    )

    # Check if aggregations are present
    if "avg" in metrics:
        expected_avg = sum(expected_values) / len(expected_values)
        assert abs(metrics["avg"] - expected_avg) < 0.01, (
            f"Average mismatch: expected {expected_avg}, got {metrics['avg']}"
        )

    if "max" in metrics:
        assert metrics["max"] == max(expected_values), (
            f"Max mismatch: expected {max(expected_values)}, got {metrics['max']}"
        )

    if "min" in metrics:
        assert metrics["min"] == min(expected_values), (
            f"Min mismatch: expected {min(expected_values)}, got {metrics['min']}"
        )

    print("✅ Output verification passed!")


def test_basic_functionality():
    """Test basic collector functionality."""

    collector_script = Path(__file__).parent / "dummy_collector.py"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"

        # Create sample data
        created_files = create_sample_data_files(input_dir)
        expected_values = [
            10.5,
            15.2,
            8.7,
            12.1,
            20.0,
        ]  # "result" field from sample data (excluding error cases)

        # Run collector with default settings
        result = run_collector_test(
            collector_script,
            input_dir,
            output_dir,
            metric_key="result",
            aggregation="all",
            debug=True,
        )

        assert result.returncode == 0, (
            f"Collector failed with return code {result.returncode}"
        )

        # Verify output
        verify_output(output_dir, expected_values)


def test_with_parameters():
    """Test collector with various parameters."""

    collector_script = Path(__file__).parent / "dummy_collector.py"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"

        # Create sample data with some error cases
        created_files = create_sample_data_files(input_dir)
        expected_values = [
            10.5,
            15.2,
            8.7,
            12.1,
            20.0,
        ]  # "result" field (valid values only)

        # Run collector with different metric key and prefix
        result = run_collector_test(
            collector_script,
            input_dir,
            output_dir,
            metric_key="result",
            aggregation="avg",
            prefix="test",
            debug=True,
            collector="yes",  # compatibility parameter
        )

        assert result.returncode == 0, (
            f"Collector failed with return code {result.returncode}"
        )

        # Check that prefix was applied
        metrics_file = output_dir / "metrics.json"
        with open(metrics_file, "r") as f:
            metrics = json.load(f)

        assert "test_avg" in metrics, "Prefix not applied to avg"
        assert "test_count" in metrics, "Prefix not applied to count"

        print("✅ Parameter test passed!")


def test_no_files_found():
    """Test collector behavior when no files are found."""

    collector_script = Path(__file__).parent / "dummy_collector.py"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_dir = tmp_path / "empty"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        # Run collector on empty directory
        result = run_collector_test(collector_script, input_dir, output_dir, debug=True)

        assert result.returncode == 1, (
            "Expected collector to return error code when no files found"
        )

        # Check error output
        metrics_file = output_dir / "metrics.json"
        assert metrics_file.exists(), "Error metrics file should still be created"

        with open(metrics_file, "r") as f:
            metrics = json.load(f)

        assert "error" in metrics, "Error message not found in output"

        print("✅ No files test passed!")


def test_error_handling():
    """Test collector behavior with error cases."""

    collector_script = Path(__file__).parent / "dummy_collector.py"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"

        # Create data with errors
        error_data = [
            {"path": "dataset1/D1_data.json", "data": {"result": 10.5, "error": None}},
            {
                "path": "dataset2/D2_data.json",
                "data": {"result": None, "error": "failed computation"},
            },
            {"path": "dataset3/D3_data.json", "data": {"result": 15.0, "error": None}},
        ]

        for item in error_data:
            file_path = input_dir / item["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(item["data"], f, indent=2)

        # Run collector
        result = run_collector_test(
            collector_script, input_dir, output_dir, metric_key="result", debug=True
        )

        assert result.returncode == 0, f"Collector failed: {result.returncode}"

        # Check that error cases are handled as "NA"
        metrics_file = output_dir / "metrics.json"
        with open(metrics_file, "r") as f:
            metrics = json.load(f)

        # Should only count valid results (2 files with error=None)
        assert metrics["count"] == 2, (
            f"Expected 2 valid results, got {metrics['count']}"
        )
        assert 10.5 in metrics["values"], "Expected value 10.5 not found"
        assert 15.0 in metrics["values"], "Expected value 15.0 not found"

        print("✅ Error handling test passed!")


def main():
    """Run all tests."""

    print("=== Testing Dummy Metric Collector ===")

    collector_script = Path(__file__).parent / "dummy_collector.py"
    if not collector_script.exists():
        print(f"❌ Collector script not found: {collector_script}")
        return 1

    try:
        print("\n--- Test 1: Basic Functionality ---")
        test_basic_functionality()

        print("\n--- Test 2: Parameter Handling ---")
        test_with_parameters()

        print("\n--- Test 3: No Files Found ---")
        test_no_files_found()

        print("\n--- Test 4: Error Handling ---")
        test_error_handling()

        print("\n🎉 All tests passed!")
        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
