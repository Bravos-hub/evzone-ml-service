"""
Unit tests for synthetic data generation.
"""
from pathlib import Path

import pandas as pd

from src.ml.data import synthetic_generator as sg


def test_sigmoid_bounds():
    assert sg._sigmoid(-100) < 0.01
    assert sg._sigmoid(0) == 0.5
    assert sg._sigmoid(100) > 0.99


def test_generate_synthetic_charger_metrics():
    df = sg.generate_synthetic_charger_metrics(n_rows=10, n_chargers=3, seed=1)
    assert len(df) == 10
    assert {"charger_id", "connector_status", "error_codes", "metadata"}.issubset(df.columns)


def test_generate_training_dataset():
    base = sg.generate_synthetic_charger_metrics(n_rows=10, n_chargers=3, seed=2)
    train = sg.generate_training_dataset(base)
    assert "failure_probability_synth" in train.columns
    assert "failure_within_30d_label" in train.columns
    assert train["failure_within_30d_label"].isin([0, 1]).all()


def test_generate_synthetic_battery_pack_metrics():
    rows = sg.generate_synthetic_battery_pack_metrics(n_rows=5, n_packs=2, seed=3)
    assert len(rows) == 5
    assert {"pack_id", "station_id", "timestamp"}.issubset(rows[0].keys())


def test_save_datasets(tmp_path):
    original_metrics = sg.generate_synthetic_charger_metrics
    original_packs = sg.generate_synthetic_battery_pack_metrics

    def small_metrics(**kwargs):
        return original_metrics(n_rows=30, n_chargers=3, seed=7)

    def small_packs(**kwargs):
        return original_packs(n_rows=10, n_packs=2, seed=7)

    sg.generate_synthetic_charger_metrics = small_metrics
    sg.generate_synthetic_battery_pack_metrics = small_packs
    try:
        outputs = sg.save_datasets(Path(tmp_path))
    finally:
        sg.generate_synthetic_charger_metrics = original_metrics
        sg.generate_synthetic_battery_pack_metrics = original_packs

    for name, path in outputs.items():
        assert path.exists(), f"Missing {name}"
