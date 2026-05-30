"""macOS GUI for Basketball Inability Analyzer using Tkinter/ttk."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from dataclasses import asdict

from src.models import Player, GameStats, Position, CompetitionLevel, Weakness
from src.analyzer import WeaknessAnalyzer
from src.benchmarks import get_display_name
from src.calculator import (
    true_shooting_pct,
    effective_fg_pct,
    assist_to_turnover_ratio,
)


COLORS = {
    "bg": "#f5f5f7",
    "card": "#ffffff",
    "text": "#1d1d1f",
    "subtext": "#86868b",
    "accent": "#007aff",
    "danger": "#ff3b30",
    "warning": "#ff9500",
    "success": "#34c759",
    "border": "#d2d2d7",
    "severity_high": "#ff3b30",
    "severity_med": "#ff9500",
    "severity_low": "#007aff",
}

FONT_FAMILY = "Helvetica Neue"


class BasketballAnalyzerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Basketball Inability Analyzer")
        self.root.geometry("900x720")
        self.root.minsize(800, 600)
        self.root.configure(bg=COLORS["bg"])

        self.analyzer = WeaknessAnalyzer()
        self.current_result = None
        self.compare_results: list = []

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("aqua")

        style.configure("Title.TLabel", font=(FONT_FAMILY, 20, "bold"),
                        foreground=COLORS["text"], background=COLORS["bg"])
        style.configure("Heading.TLabel", font=(FONT_FAMILY, 14, "bold"),
                        foreground=COLORS["text"], background=COLORS["card"])
        style.configure("Subtext.TLabel", font=(FONT_FAMILY, 11),
                        foreground=COLORS["subtext"], background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["card"])
        style.configure("DarkBg.TFrame", background=COLORS["bg"])

        style.configure("Primary.TButton", font=(FONT_FAMILY, 12),
                        background=COLORS["accent"])
        style.configure("Danger.TButton", font=(FONT_FAMILY, 12),
                        background=COLORS["danger"])

        style.configure("Field.TLabel", font=(FONT_FAMILY, 11),
                        foreground=COLORS["text"], background=COLORS["card"])

    def _build_ui(self):
        self._build_title_bar()
        self._build_notebook()

    def _build_title_bar(self):
        bar = ttk.Frame(self.root, style="DarkBg.TFrame")
        bar.pack(fill=tk.X, padx=24, pady=(24, 8))

        ttk.Label(bar, text="🏀  Basketball Inability Analyzer",
                  style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(bar, text="Find your weaknesses. Fix your game.",
                  style="Subtext.TLabel").pack(side=tk.LEFT, padx=(16, 0),
                                               pady=(6, 0))

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 20))

        self.tab_analyze = ttk.Frame(self.notebook)
        self.tab_compare = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_analyze, text="  Analyze  ")
        self.notebook.add(self.tab_compare, text="  Compare  ")
        self.notebook.add(self.tab_history, text="  Saved Reports  ")

        self._build_analyze_tab()
        self._build_compare_tab()
        self._build_history_tab()

    # ── ANALYZE TAB ──────────────────────────────────────────────

    def _build_analyze_tab(self):
        paned = ttk.PanedWindow(self.tab_analyze, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = ttk.Frame(paned, style="Card.TFrame")
        paned.add(left, weight=45)

        right = ttk.Frame(paned, style="Card.TFrame")
        paned.add(right, weight=55)

        self._build_input_form(left)
        self._build_result_panel(right)

    def _build_input_form(self, parent):
        canvas = tk.Canvas(parent, bg=COLORS["card"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style="Card.TFrame")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _bind_mousewheel(widget):
            widget.bind("<MouseWheel>", lambda e: canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"))

        _bind_mousewheel(canvas)
        _bind_mousewheel(scroll_frame)

        pad = {"padx": 16, "pady": 4, "sticky": "w"}

        ttk.Label(scroll_frame, text="Player Info",
                  style="Heading.TLabel").grid(row=0, column=0, columnspan=2,
                                               padx=16, pady=(16, 10), sticky="w")

        self.fields: dict[str, tk.Widget] = {}

        row = 1
        ttk.Label(scroll_frame, text="Name", style="Field.TLabel").grid(
            row=row, column=0, **pad)
        self.fields["name"] = ttk.Entry(scroll_frame, width=24, font=(FONT_FAMILY, 12))
        self.fields["name"].grid(row=row, column=1, **pad)

        row = 2
        ttk.Label(scroll_frame, text="Position", style="Field.TLabel").grid(
            row=row, column=0, **pad)
        self.fields["position"] = ttk.Combobox(
            scroll_frame, values=[p.value for p in Position],
            state="readonly", width=22, font=(FONT_FAMILY, 12))
        self.fields["position"].set("Shooting Guard")
        self.fields["position"].grid(row=row, column=1, **pad)

        row = 3
        ttk.Label(scroll_frame, text="Level", style="Field.TLabel").grid(
            row=row, column=0, **pad)
        self.fields["level"] = ttk.Combobox(
            scroll_frame, values=[l.value for l in CompetitionLevel],
            state="readonly", width=22, font=(FONT_FAMILY, 12))
        self.fields["level"].set("high_school")
        self.fields["level"].grid(row=row, column=1, **pad)

        row = 4
        ttk.Label(scroll_frame, text="Games Played", style="Field.TLabel").grid(
            row=row, column=0, **pad)
        self.fields["games_played"] = ttk.Entry(scroll_frame, width=24,
                                                font=(FONT_FAMILY, 12))
        self.fields["games_played"].insert(0, "20")
        self.fields["games_played"].grid(row=row, column=1, **pad)

        row = 5
        ttk.Label(scroll_frame, text="Minutes/Game", style="Field.TLabel").grid(
            row=row, column=0, **pad)
        self.fields["minutes_per_game"] = ttk.Entry(scroll_frame, width=24,
                                                    font=(FONT_FAMILY, 12))
        self.fields["minutes_per_game"].insert(0, "28")
        self.fields["minutes_per_game"].grid(row=row, column=1, **pad)

        ttk.Label(scroll_frame, text="Per-Game Stats",
                  style="Heading.TLabel").grid(row=6, column=0, columnspan=2,
                                               padx=16, pady=(20, 10), sticky="w")

        stat_fields = [
            ("points_per_game", "Points"),
            ("assists_per_game", "Assists"),
            ("rebounds_per_game", "Rebounds"),
            ("steals_per_game", "Steals"),
            ("blocks_per_game", "Blocks"),
            ("turnovers_per_game", "Turnovers"),
        ]
        for i, (key, label) in enumerate(stat_fields):
            r = 7 + i
            ttk.Label(scroll_frame, text=label, style="Field.TLabel").grid(
                row=r, column=0, **pad)
            self.fields[key] = ttk.Entry(scroll_frame, width=24,
                                         font=(FONT_FAMILY, 12))
            self.fields[key].insert(0, "0.0")
            self.fields[key].grid(row=r, column=1, **pad)

        ttk.Label(scroll_frame, text="Shooting %",
                  style="Heading.TLabel").grid(row=13, column=0, columnspan=2,
                                               padx=16, pady=(20, 10), sticky="w")

        pct_fields = [
            ("field_goal_pct", "FG% (0.xx)"),
            ("three_point_pct", "3P% (0.xx)"),
            ("free_throw_pct", "FT% (0.xx)"),
        ]
        for i, (key, label) in enumerate(pct_fields):
            r = 14 + i
            ttk.Label(scroll_frame, text=label, style="Field.TLabel").grid(
                row=r, column=0, **pad)
            self.fields[key] = ttk.Entry(scroll_frame, width=24,
                                         font=(FONT_FAMILY, 12))
            self.fields[key].insert(0, "0.00")
            self.fields[key].grid(row=r, column=1, **pad)

        btn_frame = ttk.Frame(scroll_frame, style="Card.TFrame")
        btn_frame.grid(row=18, column=0, columnspan=2, pady=(20, 16), padx=16)

        ttk.Button(btn_frame, text="Analyze", command=self._run_analysis).pack(
            side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Load JSON...",
                   command=self._load_player_json).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Clear", command=self._clear_form).pack(
            side=tk.LEFT, padx=4)

    def _build_result_panel(self, parent):
        header = ttk.Frame(parent, style="Card.TFrame")
        header.pack(fill=tk.X, padx=16, pady=(16, 8))

        self.result_title = ttk.Label(header, text="Analysis Results",
                                      style="Heading.TLabel")
        self.result_title.pack(side=tk.LEFT)

        self.score_label = ttk.Label(header, text="", font=(FONT_FAMILY, 28, "bold"),
                                     foreground=COLORS["accent"],
                                     background=COLORS["card"])
        self.score_label.pack(side=tk.RIGHT)

        self.summary_label = ttk.Label(parent, text="Enter stats and click Analyze.",
                                       font=(FONT_FAMILY, 11),
                                       foreground=COLORS["subtext"],
                                       background=COLORS["card"], wraplength=420)
        self.summary_label.pack(fill=tk.X, padx=16, pady=(0, 8))

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16)

        self.result_tree = ttk.Treeview(
            parent,
            columns=("rank", "category", "value", "benchmark", "severity"),
            show="headings",
            height=12,
        )
        self.result_tree.heading("rank", text="#", anchor="center")
        self.result_tree.heading("category", text="Category")
        self.result_tree.heading("value", text="Value", anchor="center")
        self.result_tree.heading("benchmark", text="Benchmark", anchor="center")
        self.result_tree.heading("severity", text="Severity", anchor="center")

        self.result_tree.column("rank", width=30, anchor="center")
        self.result_tree.column("category", width=140)
        self.result_tree.column("value", width=60, anchor="center")
        self.result_tree.column("benchmark", width=100, anchor="center")
        self.result_tree.column("severity", width=80, anchor="center")

        self.result_tree.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        self.recommendation_text = tk.Text(
            parent, height=5, wrap=tk.WORD, font=(FONT_FAMILY, 11),
            bg=COLORS["card"], fg=COLORS["text"], relief=tk.FLAT,
            borderwidth=0, padx=4, pady=4, state=tk.DISABLED)
        self.recommendation_text.pack(fill=tk.X, padx=16, pady=(0, 2))

        self.recommendation_text.tag_configure("bold",
                                               font=(FONT_FAMILY, 11, "bold"))
        self.recommendation_text.tag_configure("rec",
                                               font=(FONT_FAMILY, 11),
                                               foreground=COLORS["subtext"])

        btn_bar = ttk.Frame(parent, style="Card.TFrame")
        btn_bar.pack(fill=tk.X, padx=16, pady=(2, 12))
        ttk.Button(btn_bar, text="Export Report",
                   command=self._export_report).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_bar, text="Add to Compare",
                   command=self._add_to_compare).pack(side=tk.LEFT)

    # ── COMPARE TAB ──────────────────────────────────────────────

    def _build_compare_tab(self):
        self.compare_frame = ttk.Frame(self.tab_compare, style="Card.TFrame")
        self.compare_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.compare_text = tk.Text(
            self.compare_frame, wrap=tk.WORD,
            font=(FONT_FAMILY, 13), bg=COLORS["card"], fg=COLORS["text"],
            relief=tk.FLAT, borderwidth=0, padx=20, pady=20, state=tk.DISABLED)
        self.compare_text.pack(fill=tk.BOTH, expand=True)

        self.compare_text.tag_configure("h1", font=(FONT_FAMILY, 18, "bold"),
                                        foreground=COLORS["text"],
                                        spacing3=10)
        self.compare_text.tag_configure("h2", font=(FONT_FAMILY, 13, "bold"),
                                        foreground=COLORS["text"],
                                        spacing3=6)
        self.compare_text.tag_configure("green", foreground=COLORS["success"])
        self.compare_text.tag_configure("red", foreground=COLORS["danger"])
        self.compare_text.tag_configure("orange",
                                        foreground=COLORS["warning"])
        self.compare_text.tag_configure("normal",
                                        font=(FONT_FAMILY, 13))

        btn_frame = ttk.Frame(self.compare_frame, style="Card.TFrame")
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 12))
        ttk.Button(btn_frame, text="Clear Comparison",
                   command=self._clear_compare).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Load Player 1...",
                   command=lambda: self._load_compare_player(0)).pack(
            side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Load Player 2...",
                   command=lambda: self._load_compare_player(1)).pack(
            side=tk.LEFT, padx=4)

    # ── HISTORY TAB ──────────────────────────────────────────────

    def _build_history_tab(self):
        self.history_frame = ttk.Frame(self.tab_history, style="Card.TFrame")
        self.history_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        ttk.Label(self.history_frame,
                  text="Saved reports will appear here.",
                  font=(FONT_FAMILY, 13),
                  foreground=COLORS["subtext"],
                  background=COLORS["card"]).pack(expand=True)

        self.history_tree = ttk.Treeview(
            self.history_frame,
            columns=("player", "position", "score", "date"),
            show="headings",
            height=10,
        )
        self.history_tree.heading("player", text="Player")
        self.history_tree.heading("position", text="Position")
        self.history_tree.heading("score", text="Score")
        self.history_tree.heading("date", text="Date")
        self.history_tree.column("player", width=180)
        self.history_tree.column("position", width=120)
        self.history_tree.column("score", width=80)
        self.history_tree.column("date", width=140)
        self.history_tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        btn_frame = ttk.Frame(self.history_frame, style="Card.TFrame")
        btn_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        ttk.Button(btn_frame, text="Load Selected",
                   command=self._load_history_selected).pack(side=tk.LEFT,
                                                              padx=(0, 8))
        ttk.Button(btn_frame, text="Clear History",
                   command=self._clear_history).pack(side=tk.LEFT)

    # ── ACTIONS ──────────────────────────────────────────────────

    def _read_form(self) -> Player | None:
        try:
            name = self.fields["name"].get().strip() or "Unnamed"
            pos_str = self.fields["position"].get()
            position = next(p for p in Position if p.value == pos_str)
            lvl_str = self.fields["level"].get()
            level = CompetitionLevel(lvl_str)

            stats = GameStats(
                points_per_game=float(self.fields["points_per_game"].get()),
                assists_per_game=float(self.fields["assists_per_game"].get()),
                rebounds_per_game=float(self.fields["rebounds_per_game"].get()),
                steals_per_game=float(self.fields["steals_per_game"].get()),
                blocks_per_game=float(self.fields["blocks_per_game"].get()),
                turnovers_per_game=float(self.fields["turnovers_per_game"].get()),
                field_goal_pct=float(self.fields["field_goal_pct"].get()),
                three_point_pct=float(self.fields["three_point_pct"].get()),
                free_throw_pct=float(self.fields["free_throw_pct"].get()),
                games_played=int(self.fields["games_played"].get()),
                minutes_per_game=float(self.fields["minutes_per_game"].get()),
            )
            return Player(name=name, position=position, stats=stats,
                          competition_level=level)
        except (ValueError, KeyError, StopIteration) as e:
            messagebox.showerror("Invalid Input",
                                 f"Please check all fields.\n\n{str(e)}")
            return None

    def _run_analysis(self):
        player = self._read_form()
        if player is None:
            return

        self.current_result = self.analyzer.analyze(player)
        self._display_result(self.current_result)

    def _display_result(self, result):
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        self.score_label.configure(
            text=f"{result.overall_score:.0%}",
            foreground=(COLORS["success"] if result.overall_score >= 0.8
                        else COLORS["warning"] if result.overall_score >= 0.6
                        else COLORS["danger"]))

        p = result.player
        self.result_title.configure(
            text=f"{p.name} — {p.position.value} ({p.competition_level.value})")
        self.summary_label.configure(text=result.summary.split("\n")[3])

        for i, w in enumerate(result.weaknesses, 1):
            bench_str = f"{w.benchmark_min:.2f}→{w.benchmark_target:.2f}"
            val_str = f"{w.player_value:.3f}" if w.player_value < 1 else f"{w.player_value:.1f}"
            tag = f"sev_{i}"
            self.result_tree.insert("", tk.END, values=(
                i, w.category, val_str, bench_str, f"{w.severity:.0%}"),
                tags=(tag,))
            if w.severity > 0.5:
                self.result_tree.tag_configure(tag,
                                               foreground=COLORS["danger"])
            elif w.severity > 0.25:
                self.result_tree.tag_configure(tag,
                                               foreground=COLORS["warning"])

        self.recommendation_text.configure(state=tk.NORMAL)
        self.recommendation_text.delete("1.0", tk.END)
        if result.weaknesses:
            w = result.weaknesses[0]
            self.recommendation_text.insert(
                "1.0", f"Top Priority: {w.category}\n", "bold")
            self.recommendation_text.insert(tk.END, w.recommendation, "rec")
        self.recommendation_text.configure(state=tk.DISABLED)

        self._save_to_history(result)

    def _load_player_json(self):
        path = filedialog.askopenfilename(
            title="Load Player Data",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list):
                data = data[0]

            self.fields["name"].delete(0, tk.END)
            self.fields["name"].insert(0, data.get("name", ""))
            pos_val = data.get("position", "SG")
            pos_map = {p.name: p.value for p in Position}
            self.fields["position"].set(pos_map.get(pos_val, "Shooting Guard"))
            self.fields["level"].set(data.get("competition_level", "high_school"))

            for key in ["games_played", "minutes_per_game", "points_per_game",
                        "assists_per_game", "rebounds_per_game", "steals_per_game",
                        "blocks_per_game", "turnovers_per_game", "field_goal_pct",
                        "three_point_pct", "free_throw_pct"]:
                if key in data and key in self.fields:
                    self.fields[key].delete(0, tk.END)
                    self.fields[key].insert(0, str(data[key]))
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def _clear_form(self):
        for key, widget in self.fields.items():
            if isinstance(widget, ttk.Entry):
                widget.delete(0, tk.END)
                if key == "games_played":
                    widget.insert(0, "20")
                elif key == "minutes_per_game":
                    widget.insert(0, "28")
                elif key.startswith("field_goal") or key.startswith(
                        "three_point") or key.startswith("free_throw"):
                    widget.insert(0, "0.00")
                else:
                    widget.insert(0, "0.0")

    def _export_report(self):
        if self.current_result is None:
            messagebox.showinfo("No Data", "Run an analysis first.")
            return

        path = filedialog.asksaveasfilename(
            title="Export Report",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("JSON", "*.json"),
                       ("All files", "*.*")])
        if not path:
            return

        r = self.current_result
        p = r.player
        if path.endswith(".json"):
            output = {
                "player": p.name,
                "position": p.position.value,
                "level": p.competition_level.value,
                "overall_score": r.overall_score,
                "weaknesses": [
                    {"category": w.category, "severity": w.severity,
                     "player_value": w.player_value,
                     "benchmark_min": w.benchmark_min,
                     "benchmark_target": w.benchmark_target,
                     "recommendation": w.recommendation}
                    for w in r.weaknesses
                ],
                "strengths": r.strengths,
            }
            with open(path, "w") as f:
                json.dump(output, f, indent=2)
        else:
            lines = [
                f"# {p.name} — Basketball Weakness Report",
                "",
                f"**Position:** {p.position.value} | **Level:** {p.competition_level.value}",
                f"**Overall Score:** {r.overall_score:.0%}",
                "",
                "## Weaknesses",
                "",
                "| # | Category | Value | Benchmark | Severity | Recommendation |",
                "|---|----------|-------|-----------|----------|----------------|",
            ]
            for i, w in enumerate(r.weaknesses, 1):
                bench = f"{w.benchmark_min:.2f} → {w.benchmark_target:.2f}"
                val = f"{w.player_value:.3f}" if w.player_value < 1 else f"{w.player_value:.1f}"
                lines.append(
                    f"| {i} | {w.category} | {val} | {bench} | {w.severity:.0%} | {w.recommendation} |")
            lines += ["", "## Strengths", ""]
            for s in r.strengths:
                lines.append(f"- {s}")
            with open(path, "w") as f:
                f.write("\n".join(lines))

        messagebox.showinfo("Export Complete",
                            f"Report saved to:\n{path}")

    def _add_to_compare(self):
        if self.current_result is None:
            messagebox.showinfo("No Data", "Run an analysis first.")
            return
        if len(self.compare_results) < 2:
            self.compare_results.append(self.current_result)
            self._refresh_compare_view()
        if len(self.compare_results) == 2:
            messagebox.showinfo("Compare Ready",
                                "Compare tab now has both players loaded.")

    def _refresh_compare_view(self):
        self.compare_text.configure(state=tk.NORMAL)
        self.compare_text.delete("1.0", tk.END)
        if len(self.compare_results) == 0:
            self.compare_text.insert("1.0",
                                     "Add players from the Analyze tab to compare them.\n\n",
                                     "normal")
        elif len(self.compare_results) == 1:
            r = self.compare_results[0]
            self.compare_text.insert("1.0",
                                     f"Player 1: {r.player.name}\nAdd a second player to compare.\n",
                                     "normal")
        else:
            r1, r2 = self.compare_results
            self.compare_text.insert("1.0",
                                     f"Comparison: {r1.player.name} vs {r2.player.name}\n",
                                     "h1")
            self.compare_text.insert(tk.END,
                                     f"{'=' * 55}\n\n", "normal")
            self.compare_text.insert(tk.END,
                                     f"{'Category':<24} {r1.player.name:<14} {r2.player.name:<14}\n",
                                     "h2")
            self.compare_text.insert(tk.END, f"{'-' * 52}\n", "normal")

            all_cats = set()
            for w in r1.weaknesses + r2.weaknesses:
                all_cats.add(w.category)
            for cat in sorted(all_cats):
                w1 = next((w for w in r1.weaknesses if w.category == cat), None)
                w2 = next((w for w in r2.weaknesses if w.category == cat), None)

                def _tag(sev):
                    if sev is None:
                        return "green"
                    if sev > 0.5:
                        return "red"
                    if sev > 0.25:
                        return "orange"
                    return "green"

                s1_str = f"{w1.severity:.0%}" if w1 else "✓ OK"
                s2_str = f"{w2.severity:.0%}" if w2 else "✓ OK"
                t1 = _tag(w1.severity if w1 else None)
                t2 = _tag(w2.severity if w2 else None)

                self.compare_text.insert(tk.END,
                                         f"{cat:<24} ", "normal")
                self.compare_text.insert(tk.END, f"{s1_str:<14}", t1)
                self.compare_text.insert(tk.END, f" {s2_str:<14}\n", t2)

            self.compare_text.insert(tk.END, "\n", "normal")
            if r1.weaknesses:
                self.compare_text.insert(tk.END,
                                         f"🔴 {r1.player.name}: {r1.weaknesses[0].category}\n",
                                         "red")
            if r2.weaknesses:
                self.compare_text.insert(tk.END,
                                         f"🔴 {r2.player.name}: {r2.weaknesses[0].category}\n",
                                         "red")
        self.compare_text.configure(state=tk.DISABLED)

    def _clear_compare(self):
        self.compare_results.clear()
        self._refresh_compare_view()

    def _load_compare_player(self, slot: int):
        path = filedialog.askopenfilename(
            title=f"Load Player {slot + 1}",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list):
                data = data[0]
            stats = GameStats(
                **{k: v for k, v in data.items()
                   if k in GameStats.__dataclass_fields__})
            pos = Position[data.get("position", "SG")]
            level = CompetitionLevel(data.get("competition_level", "high_school"))
            player = Player(name=data.get("name", "Unknown"), position=pos,
                            stats=stats, competition_level=level)
            result = self.analyzer.analyze(player)

            if slot < len(self.compare_results):
                self.compare_results[slot] = result
            else:
                while len(self.compare_results) <= slot:
                    self.compare_results.append(None)
                self.compare_results[slot] = result
            self._refresh_compare_view()
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    # ── HISTORY ──────────────────────────────────────────────────

    def _save_to_history(self, result):
        import datetime
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        p = result.player
        self.history_tree.insert("", 0, values=(
            p.name, p.position.value, f"{result.overall_score:.0%}", date_str))

    def _load_history_selected(self):
        sel = self.history_tree.selection()
        if not sel:
            return
        values = self.history_tree.item(sel[0], "values")
        messagebox.showinfo("History",
                            f"Player: {values[0]}\n"
                            f"Score: {values[2]}\n"
                            f"Date: {values[3]}\n\n"
                            "Re-enter stats and re-analyze to view full report.")

    def _clear_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

    # ── RUN ──────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


def main():
    app = BasketballAnalyzerApp()
    app.run()


if __name__ == "__main__":
    main()
