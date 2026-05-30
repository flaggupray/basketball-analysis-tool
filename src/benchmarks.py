"""Position-based benchmark definitions for different competition levels.

Each stat is defined as [minimum_acceptable, target_value].
Falling below the minimum triggers a weakness flag with proportional severity.
"""

from src.models import Position, CompetitionLevel

Benchmark = dict[str, list[float]]

BENCHMARKS: dict[str, dict[str, Benchmark]] = {
    "PG": {
        "high_school": {
            "points_per_game": [7, 14],
            "assists_per_game": [3, 6],
            "rebounds_per_game": [2, 4],
            "steals_per_game": [1.0, 2.0],
            "blocks_per_game": [0.1, 0.5],
            "turnovers_per_game": [4.0, 2.0],
            "field_goal_pct": [0.38, 0.45],
            "three_point_pct": [0.30, 0.38],
            "free_throw_pct": [0.65, 0.80],
        },
        "college": {
            "points_per_game": [8, 16],
            "assists_per_game": [3.5, 6.5],
            "rebounds_per_game": [2.5, 4.5],
            "steals_per_game": [1.0, 2.0],
            "blocks_per_game": [0.1, 0.5],
            "turnovers_per_game": [3.5, 2.0],
            "field_goal_pct": [0.40, 0.47],
            "three_point_pct": [0.33, 0.40],
            "free_throw_pct": [0.70, 0.85],
        },
        "pro": {
            "points_per_game": [10, 20],
            "assists_per_game": [4, 8],
            "rebounds_per_game": [3, 5],
            "steals_per_game": [1.0, 2.0],
            "blocks_per_game": [0.1, 0.5],
            "turnovers_per_game": [3.0, 1.8],
            "field_goal_pct": [0.42, 0.48],
            "three_point_pct": [0.35, 0.42],
            "free_throw_pct": [0.75, 0.88],
        },
    },
    "SG": {
        "high_school": {
            "points_per_game": [8, 16],
            "assists_per_game": [1.5, 3.5],
            "rebounds_per_game": [2, 5],
            "steals_per_game": [0.8, 1.5],
            "blocks_per_game": [0.2, 0.6],
            "turnovers_per_game": [3.5, 2.0],
            "field_goal_pct": [0.40, 0.47],
            "three_point_pct": [0.32, 0.40],
            "free_throw_pct": [0.68, 0.82],
        },
        "college": {
            "points_per_game": [10, 18],
            "assists_per_game": [2, 4],
            "rebounds_per_game": [3, 6],
            "steals_per_game": [0.8, 1.5],
            "blocks_per_game": [0.2, 0.6],
            "turnovers_per_game": [3.0, 1.8],
            "field_goal_pct": [0.42, 0.49],
            "three_point_pct": [0.35, 0.42],
            "free_throw_pct": [0.72, 0.85],
        },
        "pro": {
            "points_per_game": [12, 22],
            "assists_per_game": [2.5, 4.5],
            "rebounds_per_game": [3, 6],
            "steals_per_game": [0.8, 1.5],
            "blocks_per_game": [0.2, 0.6],
            "turnovers_per_game": [2.5, 1.5],
            "field_goal_pct": [0.43, 0.50],
            "three_point_pct": [0.36, 0.43],
            "free_throw_pct": [0.76, 0.88],
        },
    },
    "SF": {
        "high_school": {
            "points_per_game": [8, 16],
            "assists_per_game": [1.5, 3.5],
            "rebounds_per_game": [3, 7],
            "steals_per_game": [0.7, 1.5],
            "blocks_per_game": [0.3, 0.8],
            "turnovers_per_game": [3.5, 2.0],
            "field_goal_pct": [0.40, 0.48],
            "three_point_pct": [0.30, 0.38],
            "free_throw_pct": [0.65, 0.80],
        },
        "college": {
            "points_per_game": [10, 18],
            "assists_per_game": [2, 4],
            "rebounds_per_game": [4, 8],
            "steals_per_game": [0.8, 1.5],
            "blocks_per_game": [0.4, 1.0],
            "turnovers_per_game": [3.0, 1.8],
            "field_goal_pct": [0.42, 0.50],
            "three_point_pct": [0.33, 0.40],
            "free_throw_pct": [0.70, 0.85],
        },
        "pro": {
            "points_per_game": [12, 22],
            "assists_per_game": [2.5, 4.5],
            "rebounds_per_game": [5, 9],
            "steals_per_game": [0.8, 1.5],
            "blocks_per_game": [0.5, 1.2],
            "turnovers_per_game": [2.5, 1.5],
            "field_goal_pct": [0.44, 0.51],
            "three_point_pct": [0.35, 0.42],
            "free_throw_pct": [0.74, 0.87],
        },
    },
    "PF": {
        "high_school": {
            "points_per_game": [6, 14],
            "assists_per_game": [1, 3],
            "rebounds_per_game": [5, 10],
            "steals_per_game": [0.5, 1.2],
            "blocks_per_game": [0.5, 1.5],
            "turnovers_per_game": [3.0, 1.8],
            "field_goal_pct": [0.42, 0.50],
            "three_point_pct": [0.25, 0.35],
            "free_throw_pct": [0.60, 0.75],
        },
        "college": {
            "points_per_game": [8, 16],
            "assists_per_game": [1.5, 3.5],
            "rebounds_per_game": [6, 11],
            "steals_per_game": [0.5, 1.2],
            "blocks_per_game": [0.8, 1.8],
            "turnovers_per_game": [2.5, 1.5],
            "field_goal_pct": [0.44, 0.52],
            "three_point_pct": [0.28, 0.38],
            "free_throw_pct": [0.64, 0.78],
        },
        "pro": {
            "points_per_game": [10, 18],
            "assists_per_game": [2, 4],
            "rebounds_per_game": [7, 12],
            "steals_per_game": [0.6, 1.2],
            "blocks_per_game": [0.8, 2.0],
            "turnovers_per_game": [2.0, 1.3],
            "field_goal_pct": [0.46, 0.54],
            "three_point_pct": [0.32, 0.40],
            "free_throw_pct": [0.68, 0.82],
        },
    },
    "C": {
        "high_school": {
            "points_per_game": [6, 14],
            "assists_per_game": [0.5, 2],
            "rebounds_per_game": [6, 12],
            "steals_per_game": [0.3, 0.8],
            "blocks_per_game": [1.0, 2.5],
            "turnovers_per_game": [2.5, 1.5],
            "field_goal_pct": [0.45, 0.55],
            "three_point_pct": [0.15, 0.30],
            "free_throw_pct": [0.50, 0.70],
        },
        "college": {
            "points_per_game": [8, 16],
            "assists_per_game": [0.8, 2.5],
            "rebounds_per_game": [7, 13],
            "steals_per_game": [0.3, 0.8],
            "blocks_per_game": [1.5, 3.0],
            "turnovers_per_game": [2.0, 1.3],
            "field_goal_pct": [0.48, 0.58],
            "three_point_pct": [0.18, 0.33],
            "free_throw_pct": [0.55, 0.73],
        },
        "pro": {
            "points_per_game": [10, 18],
            "assists_per_game": [1, 3],
            "rebounds_per_game": [8, 14],
            "steals_per_game": [0.3, 0.8],
            "blocks_per_game": [1.5, 3.0],
            "turnovers_per_game": [1.8, 1.2],
            "field_goal_pct": [0.50, 0.60],
            "three_point_pct": [0.20, 0.35],
            "free_throw_pct": [0.58, 0.75],
        },
    },
}

STAT_DISPLAY_NAMES: dict[str, str] = {
    "points_per_game": "Scoring (PPG)",
    "assists_per_game": "Playmaking (APG)",
    "rebounds_per_game": "Rebounding (RPG)",
    "steals_per_game": "Steals (SPG)",
    "blocks_per_game": "Blocks (BPG)",
    "turnovers_per_game": "Ball Security (TO)",
    "field_goal_pct": "Field Goal %",
    "three_point_pct": "Three Point %",
    "free_throw_pct": "Free Throw %",
}

RECOMMENDATIONS: dict[str, str] = {
    "points_per_game": "Increase scoring volume with spot-up shooting reps and off-ball movement drills.",
    "assists_per_game": "Improve court vision with pick-and-roll read progressions and drive-and-kick drills.",
    "rebounds_per_game": "Focus on box-out technique and pursuit angles. Add rebounding-specific conditioning.",
    "steals_per_game": "Work on passing-lane anticipation and on-ball defensive pressure with 1-on-1 full-court drills.",
    "blocks_per_game": "Develop timing on help-side rotations and verticality discipline at the rim.",
    "turnovers_per_game": "Reduce live-ball turnovers: 2-on-1 pressure ball-handling drills and decision-making under duress.",
    "field_goal_pct": "Improve shot selection and finishing: Mikan drills, off-hand layups, and mid-range catch-and-shoot reps.",
    "three_point_pct": "Form shooting progression, game-speed spot-ups, and off-screen three-point reps.",
    "free_throw_pct": "Develop a consistent pre-shot routine. Practice fatigued free throws to simulate game conditions.",
}

POSITION_WEIGHTS: dict[str, dict[str, float]] = {
    "PG": {
        "assists_per_game": 1.5, "turnovers_per_game": 1.5, "three_point_pct": 1.3,
        "steals_per_game": 1.2, "free_throw_pct": 1.0, "points_per_game": 1.0,
        "field_goal_pct": 0.9, "rebounds_per_game": 0.5, "blocks_per_game": 0.3,
    },
    "SG": {
        "points_per_game": 1.5, "three_point_pct": 1.5, "field_goal_pct": 1.2,
        "steals_per_game": 1.0, "free_throw_pct": 1.0, "turnovers_per_game": 1.0,
        "assists_per_game": 0.8, "rebounds_per_game": 0.6, "blocks_per_game": 0.4,
    },
    "SF": {
        "points_per_game": 1.2, "rebounds_per_game": 1.1, "field_goal_pct": 1.1,
        "three_point_pct": 1.0, "steals_per_game": 1.0, "assists_per_game": 1.0,
        "turnovers_per_game": 0.9, "free_throw_pct": 0.9, "blocks_per_game": 0.8,
    },
    "PF": {
        "rebounds_per_game": 1.5, "field_goal_pct": 1.3, "blocks_per_game": 1.2,
        "points_per_game": 1.0, "turnovers_per_game": 0.9, "free_throw_pct": 0.8,
        "assists_per_game": 0.7, "steals_per_game": 0.7, "three_point_pct": 0.6,
    },
    "C": {
        "rebounds_per_game": 1.5, "blocks_per_game": 1.5, "field_goal_pct": 1.3,
        "points_per_game": 1.0, "turnovers_per_game": 0.8, "free_throw_pct": 0.8,
        "assists_per_game": 0.5, "steals_per_game": 0.5, "three_point_pct": 0.3,
    },
}


def get_benchmarks(position: Position, level: CompetitionLevel) -> Benchmark:
    return BENCHMARKS[position.name][level.value]


def get_display_name(stat_key: str) -> str:
    return STAT_DISPLAY_NAMES.get(stat_key, stat_key)


def get_recommendation(stat_key: str) -> str:
    return RECOMMENDATIONS.get(stat_key, "Focus on drills to improve this area.")


def get_position_weight(position: Position, stat_key: str) -> float:
    return POSITION_WEIGHTS.get(position.name, {}).get(stat_key, 1.0)
