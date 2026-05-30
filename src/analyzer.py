"""Weakness detection engine — compares player stats against position benchmarks."""

from dataclasses import fields

from src.models import Player, GameStats, Weakness, AnalysisResult
from src.benchmarks import (
    get_benchmarks,
    get_display_name,
    get_recommendation,
    get_position_weight,
)


class WeaknessAnalyzer:
    def analyze(self, player: Player) -> AnalysisResult:
        benchmarks = get_benchmarks(player.position, player.competition_level)
        weaknesses: list[Weakness] = []
        strengths: list[str] = []

        for f in fields(GameStats):
            stat_key = f.name
            if stat_key in ("games_played", "minutes_per_game", "offensive_rebounds_per_game",
                            "defensive_rebounds_per_game", "personal_fouls_per_game",
                            "fga_per_game", "fta_per_game"):
                continue

            player_val = getattr(player.stats, stat_key)
            if stat_key not in benchmarks:
                continue

            bench_min, bench_target = benchmarks[stat_key]
            weight = get_position_weight(player.position, stat_key)

            if player_val >= bench_target:
                strengths.append(get_display_name(stat_key))
                continue

            if player_val < bench_min:
                gap = bench_min - player_val
                norm_gap = gap / max(bench_min, 0.001)
                severity = min(norm_gap * weight, 1.0)
            else:
                gap = bench_target - player_val
                total_range = max(bench_target - bench_min, 0.001)
                severity = (gap / total_range) * 0.5 * weight

            weaknesses.append(Weakness(
                category=get_display_name(stat_key),
                stat_name=stat_key,
                player_value=player_val,
                benchmark_min=bench_min,
                benchmark_target=bench_target,
                severity=severity,
                recommendation=get_recommendation(stat_key),
            ))

        weaknesses.sort(key=lambda w: w.severity, reverse=True)

        if weaknesses:
            overall = 1.0 - sum(w.severity for w in weaknesses) / max(len(weaknesses), 1)
        else:
            overall = 1.0

        summary = self._build_summary(player, weaknesses, strengths, overall)

        return AnalysisResult(
            player=player,
            weaknesses=weaknesses,
            strengths=strengths,
            overall_score=overall,
            summary=summary,
        )

    def _build_summary(self, player: Player, weaknesses: list[Weakness],
                       strengths: list[str], overall: float) -> str:
        lines = [f"Weakness Report: {player.name} ({player.position.value})", "=" * 55]

        if overall >= 0.9:
            verdict = "Elite — very few holes in your game."
        elif overall >= 0.75:
            verdict = "Solid — some areas to sharpen."
        elif overall >= 0.6:
            verdict = "Developing — clear priorities below."
        else:
            verdict = "Raw — significant growth opportunities."

        lines.append(f"Overall Score: {overall:.0%} — {verdict}")
        lines.append("")

        if weaknesses:
            lines.append(f"{'Rank':<5} {'Category':<22} {'Severity':<10} Recommendation")
            lines.append("-" * 80)
            for i, w in enumerate(weaknesses, 1):
                lines.append(f"{i:<5} {w.category:<22} {w.severity:>7.0%}    {w.recommendation}")

        if strengths:
            lines.append("")
            lines.append(f"Strengths ({len(strengths)}): " + ", ".join(strengths))

        return "\n".join(lines)
