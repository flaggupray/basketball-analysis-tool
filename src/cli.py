"""Command-line interface for the Basketball Inability Analyzer."""

import argparse
import json
import sys
from pathlib import Path

from src.models import Player, GameStats, Position, CompetitionLevel
from src.analyzer import WeaknessAnalyzer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="basketball-analyzer",
        description="Analyze basketball player stats to find weaknesses.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze a player from JSON data")
    analyze.add_argument("--player", required=True, help="Player name or path to JSON file")
    analyze.add_argument("--position", choices=[p.name for p in Position], help="Position override")
    analyze.add_argument("--level", choices=[l.value for l in CompetitionLevel],
                         default="high_school", help="Competition level")
    analyze.add_argument("--json", action="store_true", help="Output as JSON")

    interactive = sub.add_parser("interactive", help="Enter stats interactively")

    compare = sub.add_parser("compare", help="Compare two players")
    compare.add_argument("--player1", required=True)
    compare.add_argument("--player2", required=True)

    report = sub.add_parser("report", help="Generate a markdown report")
    report.add_argument("--player", required=True)
    report.add_argument("--output", default="report.md")

    return parser


def _load_player_dict(data: list | dict, player_name: str | None = None) -> dict:
    """Extract a single player dict from a list or return the dict as-is."""
    if isinstance(data, list):
        if player_name:
            for entry in data:
                if entry.get("name", "").lower() == player_name.lower():
                    return entry
        return data[0]
    return data


def parse_player_from_json(path: str, position: str | None, level: str) -> Player:
    with open(path) as f:
        data = json.load(f)

    entry = _load_player_dict(data)
    stats = GameStats(**{k: v for k, v in entry.items()
                         if k in GameStats.__dataclass_fields__})

    pos = Position[position] if position else Position[entry.get("position", "SG")]
    lvl = CompetitionLevel(entry.get("competition_level", level))

    return Player(
        name=entry.get("name", Path(path).stem),
        position=pos,
        stats=stats,
        competition_level=lvl,
        age=entry.get("age"),
        team=entry.get("team"),
    )


def interactive_input() -> Player:
    print("\n=== Basketball Inability Analyzer — Interactive Input ===\n")

    name = input("Player name: ").strip()
    print("\nPositions: PG, SG, SF, PF, C")
    pos_str = input("Position: ").strip().upper()
    position = Position[pos_str]

    print("\nLevels: high_school, college, pro")
    level_str = input("Competition level [high_school]: ").strip() or "high_school"
    level = CompetitionLevel(level_str)

    print("\n--- Enter per-game averages ---")

    def _float(prompt_text: str, default: float = 0.0) -> float:
        val = input(f"{prompt_text}: ").strip()
        return float(val) if val else default

    def _int(prompt_text: str, default: int = 1) -> int:
        val = input(f"{prompt_text}: ").strip()
        return int(val) if val else default

    stats = GameStats(
        points_per_game=_float("Points per game"),
        assists_per_game=_float("Assists per game"),
        rebounds_per_game=_float("Rebounds per game"),
        steals_per_game=_float("Steals per game"),
        blocks_per_game=_float("Blocks per game"),
        turnovers_per_game=_float("Turnovers per game"),
        field_goal_pct=_float("Field goal % (e.g. 0.42)"),
        three_point_pct=_float("Three point % (e.g. 0.35)"),
        free_throw_pct=_float("Free throw % (e.g. 0.72)"),
        games_played=_int("Games played"),
        minutes_per_game=_float("Minutes per game"),
    )

    return Player(name=name, position=position, stats=stats, competition_level=level)


def cmd_analyze(args):
    if Path(args.player).exists():
        player = parse_player_from_json(args.player, args.position, args.level)
    else:
        print(f"File not found: {args.player}")
        sys.exit(1)

    analyzer = WeaknessAnalyzer()
    result = analyzer.analyze(player)

    if args.json:
        output = {
            "player": result.player.name,
            "position": result.player.position.value,
            "level": result.player.competition_level.value,
            "overall_score": result.overall_score,
            "weaknesses": [
                {
                    "category": w.category,
                    "player_value": w.player_value,
                    "benchmark_min": w.benchmark_min,
                    "benchmark_target": w.benchmark_target,
                    "severity": w.severity,
                    "recommendation": w.recommendation,
                }
                for w in result.weaknesses
            ],
            "strengths": result.strengths,
        }
        print(json.dumps(output, indent=2))
    else:
        print(result.summary)


def cmd_interactive(args):
    player = interactive_input()
    analyzer = WeaknessAnalyzer()
    result = analyzer.analyze(player)
    print(f"\n{result.summary}")


def cmd_compare(args):
    if not Path(args.player1).exists() or not Path(args.player2).exists():
        print("Both player files must exist for comparison.")
        sys.exit(1)

    analyzer = WeaknessAnalyzer()
    p1 = parse_player_from_json(args.player1, None, "high_school")
    p2 = parse_player_from_json(args.player2, None, "high_school")
    r1 = analyzer.analyze(p1)
    r2 = analyzer.analyze(p2)

    print(f"\n{'='*60}")
    print(f"  {p1.name} (Overall: {r1.overall_score:.0%})  vs  {p2.name} (Overall: {r2.overall_score:.0%})")
    print(f"{'='*60}\n")

    all_categories = set()
    for w in r1.weaknesses + r2.weaknesses:
        all_categories.add(w.category)

    print(f"{'Category':<24} {p1.name:<14} {p2.name:<14}")
    print("-" * 52)
    for cat in sorted(all_categories):
        w1 = next((w for w in r1.weaknesses if w.category == cat), None)
        w2 = next((w for w in r2.weaknesses if w.category == cat), None)
        s1 = f"{w1.severity:.0%}" if w1 else "OK"
        s2 = f"{w2.severity:.0%}" if w2 else "OK"
        print(f"{cat:<24} {s1:<14} {s2:<14}")

    print(f"\nTop weakness for {p1.name}: {r1.weaknesses[0].category}" if r1.weaknesses else f"\n{p1.name}: No weaknesses detected")
    print(f"Top weakness for {p2.name}: {r2.weaknesses[0].category}" if r2.weaknesses else f"{p2.name}: No weaknesses detected")


def cmd_report(args):
    if not Path(args.player).exists():
        print(f"File not found: {args.player}")
        sys.exit(1)

    player = parse_player_from_json(args.player, None, "high_school")
    analyzer = WeaknessAnalyzer()
    result = analyzer.analyze(player)

    lines = [
        f"# {player.name} — Basketball Weakness Report",
        "",
        f"**Position:** {player.position.value} | **Level:** {player.competition_level.value}",
        f"**Overall Score:** {result.overall_score:.0%}",
        "",
        "## Weaknesses",
        "",
        "| # | Category | Value | Benchmark | Severity | Recommendation |",
        "|---|----------|-------|-----------|----------|----------------|",
    ]

    for i, w in enumerate(result.weaknesses, 1):
        bench = f"{w.benchmark_min:.2f} → {w.benchmark_target:.2f}"
        val_fmt = f"{w.player_value:.3f}" if w.player_value < 1 else f"{w.player_value:.1f}"
        lines.append(f"| {i} | {w.category} | {val_fmt} | {bench} | {w.severity:.0%} | {w.recommendation} |")

    lines.append("")
    lines.append("## Strengths")
    lines.append("")
    if result.strengths:
        for s in result.strengths:
            lines.append(f"- {s}")
    else:
        lines.append("No areas met targets — focus on the weaknesses above.")

    with open(args.output, "w") as f:
        f.write("\n".join(lines))
    print(f"Report written to {args.output}")


def main():
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "analyze": cmd_analyze,
        "interactive": cmd_interactive,
        "compare": cmd_compare,
        "report": cmd_report,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
