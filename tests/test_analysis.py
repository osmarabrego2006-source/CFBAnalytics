"""Unit tests for the pure derived-stat functions in analysis.py.

These use small hand-built DataFrames, so they run without an API key or a
populated database.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import (  # noqa: E402
    calculate_close_games,
    calculate_matrix_sos,
    compute_correlations,
    get_organic_talent_index,
)


def test_organic_talent_index_weights_four_classes():
    df_recruiting = pd.DataFrame({
        "team": ["A"] * 4,
        "year": [2021, 2022, 2023, 2024],
        "points": [100.0, 200.0, 300.0, 400.0],  # SR, JR, SO, FR for 2024
    })
    # 400*0.20 + 300*0.30 + 200*0.35 + 100*0.15
    assert get_organic_talent_index("A", 2024, df_recruiting) == pytest.approx(255.0)


def test_organic_talent_index_missing_class_counts_as_zero():
    df_recruiting = pd.DataFrame({"team": ["A"], "year": [2024], "points": [100.0]})
    assert get_organic_talent_index("A", 2024, df_recruiting) == pytest.approx(20.0)


def test_close_games_only_counts_one_score_games():
    df_games = pd.DataFrame({
        "year": [2024, 2024, 2024],
        "home_team": ["A", "A", "B"],
        "away_team": ["B", "C", "C"],
        "home_points": [21, 42, 10],
        "away_points": [14, 7, 17],   # A wins by 7 (close), A wins by 35 (not), C wins by 7 (close)
    })
    result = calculate_close_games(df_games).set_index("team")["close_games_net"]
    assert result["A"] == 1
    assert result["B"] == -2
    assert result["C"] == 1


def test_sos_is_mean_opponent_win_pct():
    df_record = pd.DataFrame({
        "team": ["A", "B", "C"],
        "year": [2024, 2024, 2024],
        "wins": [10, 6, 3],
        "losses": [2, 6, 9],
    })
    df_games = pd.DataFrame({
        "year": [2024, 2024],
        "home_team": ["A", "A"],
        "away_team": ["B", "C"],
        "home_points": [30, 30],
        "away_points": [20, 20],
    })
    sos = calculate_matrix_sos(df_record, df_games).set_index("team")["sos"]
    assert sos["A"] == pytest.approx((0.5 + 0.25) / 2)
    assert sos["B"] == pytest.approx(10 / 12, abs=1e-4)


def test_sos_defaults_unknown_opponent_to_500():
    df_record = pd.DataFrame({"team": ["A"], "year": [2024], "wins": [1], "losses": [0]})
    df_games = pd.DataFrame({
        "year": [2024], "home_team": ["A"], "away_team": ["FCS Team"],
        "home_points": [50], "away_points": [0],
    })
    sos = calculate_matrix_sos(df_record, df_games).set_index("team")["sos"]
    assert sos["A"] == pytest.approx(0.5)


def test_compute_correlations_returns_all_predictors():
    df = pd.DataFrame({
        "wins": [2, 5, 8, 11],
        "organic_talent_index": [100, 150, 200, 250],
        "net_rating": [0.5, -0.2, 0.1, 0.3],
        "sos": [0.4, 0.5, 0.55, 0.6],
        "close_games_net": [-2, 0, 1, 3],
    })
    corr = compute_correlations(df)
    assert set(corr) == {"organic_talent_index", "net_rating", "sos", "close_games_net"}
    assert corr["organic_talent_index"] == pytest.approx(1.0)
