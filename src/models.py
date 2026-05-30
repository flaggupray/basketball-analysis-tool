"""Data models for players, game stats, and analysis results."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Position(Enum):
    PG = "Point Guard"
    SG = "Shooting Guard"
    SF = "Small Forward"
    PF = "Power Forward"
    C = "Center"


class CompetitionLevel(Enum):
    HIGH_SCHOOL = "high_school"
    COLLEGE = "college"
    PRO = "pro"


@dataclass
class GameStats:
    points_per_game: float
    assists_per_game: float
    rebounds_per_game: float
    steals_per_game: float
    blocks_per_game: float
    turnovers_per_game: float
    field_goal_pct: float
    three_point_pct: float
    free_throw_pct: float
    games_played: int
    minutes_per_game: float
    offensive_rebounds_per_game: float = 0.0
    defensive_rebounds_per_game: float = 0.0
    personal_fouls_per_game: float = 0.0
    fga_per_game: float = 0.0
    fta_per_game: float = 0.0

    def __post_init__(self):
        if self.offensive_rebounds_per_game == 0.0 and self.defensive_rebounds_per_game == 0.0:
            self.offensive_rebounds_per_game = self.rebounds_per_game * 0.25
            self.defensive_rebounds_per_game = self.rebounds_per_game * 0.75


@dataclass
class Player:
    name: str
    position: Position
    stats: GameStats
    competition_level: CompetitionLevel = CompetitionLevel.HIGH_SCHOOL
    age: Optional[int] = None
    team: Optional[str] = None


@dataclass
class Weakness:
    category: str
    stat_name: str
    player_value: float
    benchmark_min: float
    benchmark_target: float
    severity: float
    recommendation: str


@dataclass
class AnalysisResult:
    player: Player
    weaknesses: list[Weakness] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    overall_score: float = 0.0
    summary: str = ""
