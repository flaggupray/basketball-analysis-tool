"""Tests for basketball metric calculations."""

import pytest

from src.calculator import (
    true_shooting_pct,
    effective_fg_pct,
    assist_to_turnover_ratio,
    steal_rate,
    block_rate,
    turnover_rate,
    per_36,
)
from src.models import GameStats


@pytest.fixture
def sample_stats():
    return GameStats(
        points_per_game=15.0,
        assists_per_game=4.0,
        rebounds_per_game=5.0,
        steals_per_game=1.2,
        blocks_per_game=0.6,
        turnovers_per_game=3.0,
        field_goal_pct=0.44,
        three_point_pct=0.36,
        free_throw_pct=0.78,
        games_played=20,
        minutes_per_game=30.0,
        fga_per_game=12.0,
        fta_per_game=4.0,
    )


class TestCalculator:
    def test_true_shooting_pct(self, sample_stats):
        ts = true_shooting_pct(sample_stats)
        assert 0.40 < ts < 0.80, f"Expected TS% in 0.40–0.80, got {ts:.3f}"

    def test_effective_fg_pct(self, sample_stats):
        efg = effective_fg_pct(sample_stats)
        assert 0.40 < efg < 0.70, f"Expected eFG% in 0.40–0.70, got {efg:.3f}"

    def test_ast_to_to_ratio(self, sample_stats):
        ratio = assist_to_turnover_ratio(sample_stats)
        assert abs(ratio - 1.333) < 0.1

    def test_ast_to_to_zero_turnovers(self):
        stats = GameStats(15, 4, 5, 1.2, 0.6, 0, 0.44, 0.36, 0.78, 20, 30)
        assert assist_to_turnover_ratio(stats) == 4.0

    def test_steal_rate(self, sample_stats):
        sr = steal_rate(sample_stats)
        assert abs(sr - 1.44) < 0.01

    def test_block_rate(self, sample_stats):
        br = block_rate(sample_stats)
        assert abs(br - 0.72) < 0.01

    def test_turnover_rate(self, sample_stats):
        tor = turnover_rate(sample_stats)
        assert 0.10 < tor < 0.35

    def test_per_36(self):
        assert per_36(12.0, 24.0) == 18.0
        assert per_36(0, 30.0) == 0.0
        assert per_36(10.0, 0) == 0.0

    def test_zero_minutes_edge_case(self):
        stats = GameStats(10, 2, 3, 0.5, 0.2, 2, 0.40, 0.33, 0.70, 1, 0)
        assert turnover_rate(stats) == 0.0
        assert steal_rate(stats) == 0.0
