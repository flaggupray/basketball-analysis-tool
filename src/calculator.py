"""Advanced basketball metric calculations."""

from src.models import GameStats


def true_shooting_pct(stats: GameStats) -> float:
    """TS% — points per scoring attempt, accounting for 3s and FTs."""
    if stats.fga_per_game > 0:
        fga = stats.fga_per_game
    else:
        fga = stats.points_per_game / max(stats.field_goal_pct * 2, 0.01)
    if stats.fta_per_game > 0:
        fta = stats.fta_per_game
    else:
        fta = (stats.points_per_game * 0.25)
    denominator = 2 * (fga + 0.44 * fta)
    if denominator == 0:
        return 0.0
    return stats.points_per_game / denominator


def effective_fg_pct(stats: GameStats) -> float:
    """eFG% — field goal percentage weighted for 3-pointers being worth more."""
    threes_made = stats.points_per_game * 0.3 / 3
    twos_made = (stats.points_per_game * 0.7) / 2
    threes_attempted = threes_made / max(stats.three_point_pct, 0.01)
    twos_attempted = twos_made / max(stats.field_goal_pct, 0.01)
    total_attempts = threes_attempted + twos_attempted
    if total_attempts == 0:
        return 0.0
    return (twos_made + 1.5 * threes_made) / total_attempts


def assist_to_turnover_ratio(stats: GameStats) -> float:
    """AST/TO ratio."""
    if stats.turnovers_per_game == 0:
        return stats.assists_per_game
    return stats.assists_per_game / stats.turnovers_per_game


def steal_rate(stats: GameStats) -> float:
    """Steals per 36 minutes."""
    if stats.minutes_per_game == 0:
        return 0.0
    return stats.steals_per_game * 36 / stats.minutes_per_game


def block_rate(stats: GameStats) -> float:
    """Blocks per 36 minutes."""
    if stats.minutes_per_game == 0:
        return 0.0
    return stats.blocks_per_game * 36 / stats.minutes_per_game


def turnover_rate(stats: GameStats) -> float:
    """Estimated turnover percentage (possessions ended by turnover)."""
    if stats.minutes_per_game == 0:
        return 0.0
    possessions = stats.fga_per_game + 0.44 * stats.fta_per_game + stats.turnovers_per_game
    if possessions == 0:
        possessions = (stats.points_per_game / max(stats.field_goal_pct * 2, 0.01)) + stats.turnovers_per_game
    if possessions == 0:
        return 0.0
    return stats.turnovers_per_game / possessions


def per_36(per_game_stat: float, minutes_per_game: float) -> float:
    """Scale a per-game stat to per-36-minutes."""
    if minutes_per_game == 0:
        return 0.0
    return per_game_stat * 36 / minutes_per_game
