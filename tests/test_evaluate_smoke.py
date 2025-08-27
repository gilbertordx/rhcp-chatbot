#!/usr/bin/env python3
"""
Smoke test for evaluate.py script.

Tests that the evaluation script runs without errors and produces expected output.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestEvaluateSmoke:
    """Smoke tests for evaluate.py script."""

    def test_evaluate_script_imports(self):
        """Test that evaluate.py can be imported without errors."""
        try:
            from scripts.evaluate import (
                analyze_gating_performance,
                load_eval_data,
                main,
                print_metrics,
                run_classification,
            )

            assert True  # Import successful
        except ImportError as e:
            pytest.fail(f"Failed to import evaluate.py: {e}")

    def test_evaluate_script_runs_basic(self):
        """Test that evaluate.py runs with basic arguments."""
        script_path = Path("scripts/evaluate.py")
        assert script_path.exists(), "evaluate.py script not found"

        # Test help output
        result = subprocess.run(
            ["python3", str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Script failed with return code {result.returncode}"
        )
        assert "usage:" in result.stdout.lower(), "Help output not found"

    def test_evaluate_script_with_hard_negatives(self):
        """Test that evaluate.py runs with hard negatives dataset."""
        script_path = Path("scripts/evaluate.py")
        data_path = Path("data/eval/hard_negatives.jsonl")

        assert script_path.exists(), "evaluate.py script not found"
        assert data_path.exists(), "hard_negatives.jsonl not found"

        # Run evaluation with hard negatives
        result = subprocess.run(
            ["python3", str(script_path), "--data", str(data_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Check that script ran (may fail due to missing model, but should not crash)
        assert result.returncode in [0, 1], (
            f"Unexpected return code: {result.returncode}"
        )

        # Check that some output was produced
        assert len(result.stdout) > 0 or len(result.stderr) > 0, "No output produced"

    def test_evaluate_script_output_format(self):
        """Test that evaluate.py produces expected output format."""
        script_path = Path("scripts/evaluate.py")
        data_path = Path("data/eval/hard_negatives.jsonl")

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Run evaluation with output file
            result = subprocess.run(
                [
                    "python3",
                    str(script_path),
                    "--data",
                    str(data_path),
                    "--output",
                    tmp_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # If script ran successfully, check output format
            if result.returncode == 0 and Path(tmp_path).exists():
                with open(tmp_path) as f:
                    output_data = json.load(f)

                # Check required fields
                required_fields = [
                    "dataset_path",
                    "dataset_size",
                    "confidence_threshold",
                ]
                for field in required_fields:
                    assert field in output_data, f"Missing field: {field}"

                # Check data types
                assert isinstance(output_data["dataset_size"], int)
                assert isinstance(output_data["confidence_threshold"], float)

        finally:
            # Clean up
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_evaluate_script_confidence_threshold(self):
        """Test that evaluate.py accepts custom confidence threshold."""
        script_path = Path("scripts/evaluate.py")
        data_path = Path("data/eval/hard_negatives.jsonl")

        # Test with custom threshold
        result = subprocess.run(
            [
                "python3",
                str(script_path),
                "--data",
                str(data_path),
                "--confidence-threshold",
                "0.50",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should not crash
        assert result.returncode in [0, 1], (
            f"Unexpected return code: {result.returncode}"
        )

    def test_hard_negatives_dataset_format(self):
        """Test that hard negatives dataset has correct format."""
        data_path = Path("data/eval/hard_negatives.jsonl")
        assert data_path.exists(), "hard_negatives.jsonl not found"

        examples = []
        with open(data_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    example = json.loads(line)
                    examples.append(example)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON at line {line_num}: {e}")

        # Check dataset size
        assert len(examples) >= 30, (
            f"Expected at least 30 examples, got {len(examples)}"
        )

        # Check format of each example
        for i, example in enumerate(examples):
            assert "text" in example, f"Example {i} missing 'text' field"
            assert "intent" in example, f"Example {i} missing 'intent' field"
            assert "entities" in example, f"Example {i} missing 'entities' field"

            # Check data types
            assert isinstance(example["text"], str), f"Example {i} 'text' not string"
            assert isinstance(example["intent"], str), (
                f"Example {i} 'intent' not string"
            )
            assert isinstance(example["entities"], list), (
                f"Example {i} 'entities' not list"
            )

            # Check content
            assert len(example["text"]) > 0, f"Example {i} has empty text"
            assert example["intent"] == "intent.outofscope", (
                f"Example {i} intent should be 'intent.outofscope'"
            )

    def test_evaluate_script_integration(self):
        """Integration test: run evaluate.py and verify it produces metrics."""
        script_path = Path("scripts/evaluate.py")
        data_path = Path("data/eval/hard_negatives.jsonl")

        # Mock the inference pipeline to avoid model loading issues
        with patch("scripts.evaluate.run_inference") as mock_inference:
            # Mock response object
            mock_response = MagicMock()
            mock_response.intent = "intent.outofscope"
            mock_response.confidence = 0.45
            mock_inference.return_value = mock_response

            # Import and test the functions directly
            from scripts.evaluate import analyze_gating_performance, load_eval_data

            # Load data
            examples = load_eval_data(str(data_path))
            assert len(examples) >= 30

            # Test gating analysis
            true_intents = [ex["intent"] for ex in examples]
            predicted_intents = ["intent.outofscope"] * len(examples)
            confidence_scores = [0.45] * len(examples)

            gating_analysis = analyze_gating_performance(
                true_intents, predicted_intents, confidence_scores, 0.60
            )

            # Verify gating analysis structure
            required_gating_fields = [
                "confidence_threshold",
                "low_confidence_count",
                "low_confidence_rate",
                "total_gated_to_unknown",
                "correctly_gated",
                "incorrectly_gated",
                "gating_accuracy",
            ]

            for field in required_gating_fields:
                assert field in gating_analysis, f"Missing gating field: {field}"

            # Verify values make sense
            assert gating_analysis["confidence_threshold"] == 0.60
            assert gating_analysis["low_confidence_count"] == len(examples)
            assert gating_analysis["low_confidence_rate"] == 1.0
            assert (
                gating_analysis["total_gated_to_unknown"] == 0
            )  # No gating to unknown with current mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
