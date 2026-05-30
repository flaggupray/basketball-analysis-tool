# Basketball Inability Analyzer

A data-driven tool that helps basketball players identify their weaknesses by analyzing game statistics against position-based benchmarks. Move beyond guesswork — see exactly which parts of your game need work, backed by numbers.

## How It Works
a
1. **Input your stats** — points, rebounds, assists, shooting percentages, turnovers, steals, blocks across multiple games.
2. **Benchmark comparison** — your stats are compared against norms for your position (PG, SG, SF, PF, C) and competition level.
3. **Weakness scoring** — each stat category receives a deficiency score, weighted by how far you fall below the benchmark and how important that stat is for your position.
4. **Actionable output** — the tool ranks your top inabilities and suggests specific drills and focus areas.

## Metrics Analyzed

| Category | Stats |
|---|---|
| Scoring | PPG, FG%, 3P%, FT%, TS% |
| Playmaking | APG, AST/TO ratio, turnover rate |
| Rebounding | ORPG, DRPG, total RPG |
| Defense | SPG, BPG, defensive rating |
| Efficiency | PER, usage rate, offensive rating |

## Installation

### Option 1: Download DMG (macOS)

1. Go to [Releases](https://github.com/YOUR_USERNAME/basketball-analysis-tool/releases)
2. Download `BasketballAnalyzer-1.0.0.dmg`
3. Open the DMG and drag **Basketball Analyzer** into **Applications**
4. First launch: **Right-click → Open** (Gatekeeper bypass for unsigned app)

### Option 2: Build from source

```bash
git clone https://github.com/YOUR_USERNAME/basketball-analysis-tool.git
cd basketball-analysis-tool
pip install -r requirements.txt
```

### Option 3: Build your own DMG

```bash
pip install pyinstaller
bash build_dmg.sh
# DMG appears at dist/BasketballAnalyzer-1.0.0.dmg
```

## Usage

### macOS GUI (Recommended)

Launch **Basketball Analyzer.app** from Applications. Three tabs:

- **Analyze** — enter player stats and get an instant weakness breakdown
- **Compare** — side-by-side comparison of two players
- **Saved Reports** — view analysis history

### Command Line

```bash
# Analyze a single player with sample data
python -m src.cli analyze --player data/sample_players.json

# Input your own stats interactively
python -m src.cli interactive

# Compare two players side by side
python -m src.cli compare --player1 "Player A" --player2 "Player B"

# Generate a full report as markdown
python -m src.cli report --player data/sample_players.json --output report.md
```

### Using the Library

```python
from src.models import Player, GameStats, Position
from src.analyzer import WeaknessAnalyzer

player = Player(
    name="Jane Doe",
    position=Position.SG,
    stats=GameStats(
        points_per_game=12.3,
        assists_per_game=2.1,
        rebounds_per_game=3.4,
        steals_per_game=0.8,
        blocks_per_game=0.3,
        turnovers_per_game=3.2,
        field_goal_pct=0.38,
        three_point_pct=0.31,
        free_throw_pct=0.72,
        games_played=20,
        minutes_per_game=28.0,
    ),
)

analyzer = WeaknessAnalyzer()
weaknesses = analyzer.analyze(player)

for w in weaknesses[:3]:
    print(f"{w.category}: {w.severity:.0%} deficiency — {w.recommendation}")
```

## Example Output

```
=== Weakness Report: Jane Doe (SG) ===

Rank  Category      Severity  Recommendation
─────────────────────────────────────────────────────
  1   Ball Security   87%     Reduce live-ball turnovers with 2-on-1 pressure drills
  2   Playmaking      72%     Improve vision with pick-and-roll read progressions
  3   Perimeter D     61%     Close-out footwork and lateral quickness training
  4   Finishing       54%     Mikan drills and off-hand layups at game speed
```

## Position Benchmarks

Benchmarks are derived from aggregated high school and collegiate data, normalized by position. Each position has expected ranges for every stat category. You can customize benchmarks by editing `data/benchmarks.json`.

## Project Structure

```
├── src/
│   ├── __init__.py
│   ├── models.py        # Player, GameStats, Position data classes
│   ├── calculator.py    # Advanced metric calculations
│   ├── analyzer.py      # Weakness detection and scoring engine
│   ├── benchmarks.py    # Position-based benchmark definitions
│   ├── cli.py           # Command-line interface
│   └── gui.py           # macOS GUI (Tkinter)
├── data/
│   └── sample_players.json
├── tests/
│   ├── test_calculator.py
│   └── test_analyzer.py
├── build_assets/
│   ├── gui.spec         # PyInstaller spec for macOS .app
│   ├── generate_icon.py # App icon generator
│   └── icons/           # Generated .icns icon
├── build_dmg.sh         # Build script (PyInstaller + DMG)
├── requirements.txt
└── setup.py
```

## Customizing Benchmarks

Edit `data/benchmarks.json` to match your league or age group. Benchmarks are organized by position and competition level:

```json
{
  "PG": {
    "high_school": { "ppg": [8, 15], "apg": [3, 7], ... },
    "college":    { "ppg": [10, 18], "apg": [4, 8], ... }
  }
}
```

Each stat has a `[minimum, target]` range — falling below the minimum triggers a weakness flag.

## Contributing

Pull requests are welcome. Areas that need help:
- Additional stat categories (catch-and-shoot %, isolation efficiency, P&R ball-handler rating)
- Web dashboard UI
- Synergy-style video clip references for drills
- Import from common stat-tracking apps

## License

MIT
