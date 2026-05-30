"""Tests for the weakness detection engine."""

import pytest

from src.models import Player, GameStats, Position, CompetitionLevel, Weakness
from src.analyzer import WeaknessAnalyzer


@pytest.fixture
def strong_player():
    return Player(
        name="Strong Player",
        position=Position.SG,
        stats=GameStats(
            points_per_game=20.0,
            assists_per_game=5.0,
            rebounds_per_game=6.0,
            steals_per_game=1.8,
            blocks_per_game=0.8,
            turnovers_per_game=1.5,
            field_goal_pct=0.50,
            three_point_pct=0.42,
            free_throw_pct=0.88,
            games_played=30,
            minutes_per_game=32.0,
        ),
        competition_level=CompetitionLevel.COLLEGE,
    )


@pytest.fixture
def weak_player():
    return Player(
        name="Weak Player",
        position=Position.PG,
        stats=GameStats(
            points_per_game=5.0,
            assists_per_game=2.0,
            rebounds_per_game=1.5,
            steals_per_game=0.4,
            blocks_per_game=0.0,
            turnovers_per_game=6.0,
            field_goal_pct=0.30,
            three_point_pct=0.18,
            free_throw_pct=0.50,
            games_played=10,
            minutes_per_game=20.0,
        ),
        competition_level=CompetitionLevel.HIGH_SCHOOL,
    )


class TestWeaknessAnalyzer:
    def test_strong_player_high_score(self, strong_player):
        analyzer = WeaknessAnalyzer()
        result = analyzer.analyze(strong_player)
        assert result.overall_score > 0.80

    def test_weak_player_low_score(self, weak_player):
        analyzer = WeaknessAnalyzer()
        result = analyzer.analyze(weak_player)
        assert result.overall_score < 0.60

    def test_weaknesses_sorted_by_severity(self, weak_player):
        analyzer = WeaknessAnalyzer()
        result = analyzer.analyze(weak_player)
        severities = [w.severity for w in result.weaknesses]
        assert severities == sorted(severities, reverse=True)

    def test_weaknesses_have_recommendations(self, weak_player):
        analyzer = WeaknessAnalyzer()
        result = analyzer.analyze(weak_player)
        for w in result.weaknesses:
            assert len(w.recommendation) > 10

    def test_summary_contains_player_name(self, strong_player):
        analyzer = WeaknessAnalyzer()
        result = analyzer.analyze(strong_player)
        assert "Strong Player" in result.summary

    def test_different_positions_produce_different_results(self):
        pg = Player("PG", Position.PG, GameStats(15, 3, 4, 1.0, 0.2, 3, 0.42, 0.35, 0.75, 20, 30))
        c = Player("C", Position.C, GameStats(15, 3, 4, 1.0, 0.2, 3, 0.42, 0.35, 0.75, 20, 30))
        analyzer = WeaknessAnalyzer()
        r_pg = analyzer.analyze(pg)
        r_c = analyzer.analyze(c)
        assert r_pg.overall_score != r_c.overall_score or r_pg.weaknesses != r_c.weaknesses
