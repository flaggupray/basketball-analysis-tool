"""Basketball Inability Analyzer — macOS GUI with video, camera, and shot tracking."""

from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from dataclasses import asdict

import numpy as np
from PIL import Image, ImageTk

from src.models import Player, GameStats, Position, CompetitionLevel, Weakness
from src.analyzer import WeaknessAnalyzer
from src.benchmarks import get_display_name
from src.calculator import true_shooting_pct, effective_fg_pct, assist_to_turnover_ratio
from src.camera import CameraManager
from src.video_analyzer import VideoAnalyzer


# ── Theme ──────────────────────────────────────────────────────
C = {
    "bg":       "#0f0f1a",
    "card":     "#1a1a2e",
    "card2":    "#16213e",
    "accent":   "#e94560",
    "accent2":  "#533483",
    "green":    "#2ecc71",
    "orange":   "#f39c12",
    "red":      "#e74c3c",
    "text":     "#eaeaea",
    "subtext":  "#9a9ab0",
    "border":   "#2a2a4a",
    "entry_bg": "#12122a",
}
FONT = "Helvetica Neue"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Basketball Inability Analyzer")
        self.geometry("1100x780")
        self.minsize(960, 640)
        self.configure(bg=C["bg"])

        self.analyzer = WeaknessAnalyzer()
        self.camera = CameraManager()
        self.video_analyzer = VideoAnalyzer()
        self._cam_preview_job: str | None = None
        self._video_playback_job: str | None = None
        self._current_result = None
        self._compare: list = []
        self._history: list = []

        self._setup_style()
        self._build()

    def _setup_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=C["bg"], foreground=C["text"], font=(FONT, 11))
        s.configure("TNotebook", background=C["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", padding=[18, 8], font=(FONT, 12, "bold"),
                     background=C["card"], foreground=C["subtext"], borderwidth=0)
        s.map("TNotebook.Tab", selected=[("background", C["accent"]), ("foreground", "#fff")])
        s.configure("Card.TFrame", background=C["card"])
        s.configure("Dark.TFrame", background=C["bg"])
        s.configure("Title.TLabel", font=(FONT, 18, "bold"), foreground=C["text"], background=C["bg"])
        s.configure("Heading.TLabel", font=(FONT, 14, "bold"), foreground=C["text"], background=C["card"])
        s.configure("Sub.TLabel", font=(FONT, 11), foreground=C["subtext"], background=C["card"])
        s.configure("Accent.TButton", font=(FONT, 11, "bold"), background=C["accent"])
        s.configure("TLabel", background=C["card"], foreground=C["text"], font=(FONT, 11))
        s.configure("TEntry", fieldbackground=C["entry_bg"], foreground=C["text"])
        s.configure("TSeparator", background=C["border"])

    # ── Build ──────────────────────────────────────────────────

    def _build(self):
        # Title bar
        bar = ttk.Frame(self, style="Dark.TFrame")
        bar.pack(fill=tk.X, padx=24, pady=(18, 6))
        ttk.Label(bar, text="🏀  Basketball Inability Analyzer", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(bar, text="Stats · Video · Camera · Compare", style="Sub.TLabel").pack(
            side=tk.RIGHT, pady=(6, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(2, 14))

        self._build_analyze_tab()
        self._build_video_tab()
        self._build_camera_tab()
        self._build_compare_tab()
        self._build_history_tab()

    # ════════════════════════════════════════════════════════════
    #  ANALYZE TAB
    # ════════════════════════════════════════════════════════════

    def _build_analyze_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  📊 Analyze  ")
        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = ttk.Frame(pw, style="Card.TFrame")
        pw.add(left, weight=42)
        right = ttk.Frame(pw, style="Card.TFrame")
        pw.add(right, weight=58)
        self._build_form(left)
        self._build_result(right)

    def _build_form(self, parent):
        cv = tk.Canvas(parent, bg=C["card"], highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=cv.yview)
        sf = ttk.Frame(cv, style="Card.TFrame")
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        def _mw(w): w.bind("<MouseWheel>", lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"))
        _mw(cv); _mw(sf)

        p = {"padx": 14, "pady": 3, "sticky": "w"}
        self.fields: dict[str, tk.Widget] = {}

        ttk.Label(sf, text="Player Info", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, padx=14, pady=(14, 8), sticky="w")

        for r, (k, lbl) in enumerate([
            ("name", "Name"), ("position", "Position"), ("level", "Level"),
            ("games_played", "Games Played"), ("minutes_per_game", "Minutes/Game"),
        ], 1):
            ttk.Label(sf, text=lbl).grid(row=r, column=0, **p)
            if k == "position":
                w = ttk.Combobox(sf, values=[p.value for p in Position], state="readonly", width=22)
                w.set("Shooting Guard")
            elif k == "level":
                w = ttk.Combobox(sf, values=[l.value for l in CompetitionLevel], state="readonly", width=22)
                w.set("high_school")
            else:
                w = ttk.Entry(sf, width=24)
                if k == "games_played": w.insert(0, "20")
                elif k == "minutes_per_game": w.insert(0, "28")
            w.grid(row=r, column=1, **p)
            self.fields[k] = w

        ttk.Label(sf, text="Per-Game Averages", style="Heading.TLabel").grid(
            row=7, column=0, columnspan=2, padx=14, pady=(16, 8), sticky="w")

        for i, (k, lbl) in enumerate([
            ("points_per_game", "Points"), ("assists_per_game", "Assists"),
            ("rebounds_per_game", "Rebounds"), ("steals_per_game", "Steals"),
            ("blocks_per_game", "Blocks"), ("turnovers_per_game", "Turnovers"),
        ]):
            ttk.Label(sf, text=lbl).grid(row=8+i, column=0, **p)
            w = ttk.Entry(sf, width=24); w.insert(0, "0.0")
            w.grid(row=8+i, column=1, **p)
            self.fields[k] = w

        ttk.Label(sf, text="Shooting Percentages", style="Heading.TLabel").grid(
            row=15, column=0, columnspan=2, padx=14, pady=(16, 8), sticky="w")

        for i, (k, lbl) in enumerate([
            ("field_goal_pct", "FG% (0.xx)"), ("three_point_pct", "3P% (0.xx)"),
            ("free_throw_pct", "FT% (0.xx)"),
        ]):
            ttk.Label(sf, text=lbl).grid(row=16+i, column=0, **p)
            w = ttk.Entry(sf, width=24); w.insert(0, "0.00")
            w.grid(row=16+i, column=1, **p)
            self.fields[k] = w

        bf = ttk.Frame(sf, style="Card.TFrame")
        bf.grid(row=20, column=0, columnspan=2, pady=(16, 14), padx=14)
        for txt, cmd in [("Analyze", self._run_analysis), ("Load JSON…", self._load_json),
                         ("Clear", self._clear_form)]:
            ttk.Button(bf, text=txt, command=cmd).pack(side=tk.LEFT, padx=3)

    def _build_result(self, parent):
        hdr = ttk.Frame(parent, style="Card.TFrame")
        hdr.pack(fill=tk.X, padx=16, pady=(14, 6))
        self._result_title = ttk.Label(hdr, text="Analysis Results", style="Heading.TLabel")
        self._result_title.pack(side=tk.LEFT)
        self._score_lbl = tk.Label(hdr, text="—", font=(FONT, 32, "bold"),
                                   fg=C["accent"], bg=C["card"])
        self._score_lbl.pack(side=tk.RIGHT)

        self._summary_lbl = ttk.Label(parent, text="Enter stats and click Analyze.", wraplength=480)
        self._summary_lbl.pack(fill=tk.X, padx=16, pady=(0, 6))

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16)

        self._result_tree = ttk.Treeview(parent, columns=("r","cat","val","bench","sev"),
                                         show="headings", height=10)
        for c, w, a in [("r", 30, "center"), ("cat", 150, "w"), ("val", 65, "center"),
                         ("bench", 110, "center"), ("sev", 80, "center")]:
            self._result_tree.heading(c, text={"r":"#","cat":"Category","val":"Value",
                                               "bench":"Benchmark","sev":"Severity"}[c])
            self._result_tree.column(c, width=w, anchor=a)
        self._result_tree.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        self._rec_text = tk.Text(parent, height=4, wrap=tk.WORD, font=(FONT, 11),
                                 bg=C["card"], fg=C["text"], relief=tk.FLAT, border=0,
                                 padx=8, pady=6, state=tk.DISABLED)
        self._rec_text.tag_configure("b", font=(FONT, 11, "bold"), foreground=C["accent"])
        self._rec_text.tag_configure("r", foreground=C["subtext"])
        self._rec_text.pack(fill=tk.X, padx=16, pady=(0, 4))

        bb = ttk.Frame(parent, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=16, pady=(2, 10))
        ttk.Button(bb, text="Export Report", command=self._export_report).pack(side=tk.LEFT, padx=3)
        ttk.Button(bb, text="Add to Compare", command=self._add_compare).pack(side=tk.LEFT, padx=3)

    # ── Analyze actions ────────────────────────────────────────

    def _read_form(self) -> Player | None:
        try:
            name = self.fields["name"].get().strip() or "Unnamed"
            pos = next(p for p in Position if p.value == self.fields["position"].get())
            lvl = CompetitionLevel(self.fields["level"].get())
            s = GameStats(
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
            return Player(name=name, position=pos, stats=s, competition_level=lvl)
        except (ValueError, KeyError, StopIteration) as e:
            messagebox.showerror("Invalid Input", f"Check all fields.\n{str(e)}")
            return None

    def _run_analysis(self):
        p = self._read_form()
        if p is None: return
        self._current_result = self.analyzer.analyze(p)
        self._show_result(self._current_result)

    def _show_result(self, r):
        for i in self._result_tree.get_children():
            self._result_tree.delete(i)
        sc = r.overall_score
        self._score_lbl.configure(text=f"{sc:.0%}",
                                  fg=C["green"] if sc>=0.8 else C["orange"] if sc>=0.6 else C["red"])
        self._result_title.configure(text=f"{r.player.name} — {r.player.position.value}")
        lines = r.summary.split("\n")
        self._summary_lbl.configure(text=lines[3] if len(lines)>3 else "")

        for i, w in enumerate(r.weaknesses, 1):
            bs = f"{w.benchmark_min:.2f}→{w.benchmark_target:.2f}"
            vs = f"{w.player_value:.3f}" if w.player_value<1 else f"{w.player_value:.1f}"
            tag = f"s{i}"
            self._result_tree.insert("", tk.END, values=(i, w.category, vs, bs, f"{w.severity:.0%}"), tags=(tag,))
            if w.severity > 0.5: self._result_tree.tag_configure(tag, foreground=C["red"])
            elif w.severity > 0.25: self._result_tree.tag_configure(tag, foreground=C["orange"])

        self._rec_text.configure(state=tk.NORMAL)
        self._rec_text.delete("1.0", tk.END)
        if r.weaknesses:
            self._rec_text.insert("1.0", f"Top Priority: {r.weaknesses[0].category}\n", "b")
            self._rec_text.insert(tk.END, r.weaknesses[0].recommendation, "r")
        self._rec_text.configure(state=tk.DISABLED)
        self._save_history(r)

    def _load_json(self):
        p = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not p: return
        try:
            with open(p) as f: data = json.load(f)
            if isinstance(data, list): data = data[0]
            self.fields["name"].delete(0, tk.END); self.fields["name"].insert(0, data.get("name",""))
            pm = {p.name: p.value for p in Position}
            self.fields["position"].set(pm.get(data.get("position","SG"), "Shooting Guard"))
            self.fields["level"].set(data.get("competition_level","high_school"))
            for k in ["games_played","minutes_per_game","points_per_game","assists_per_game",
                      "rebounds_per_game","steals_per_game","blocks_per_game","turnovers_per_game",
                      "field_goal_pct","three_point_pct","free_throw_pct"]:
                if k in data and k in self.fields:
                    self.fields[k].delete(0, tk.END); self.fields[k].insert(0, str(data[k]))
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def _clear_form(self):
        for k, w in self.fields.items():
            if isinstance(w, ttk.Entry):
                w.delete(0, tk.END)
                d = {"games_played":"20","minutes_per_game":"28"}.get(k, "")
                if k.startswith("field_goal") or k.startswith("three_point") or k.startswith("free_throw"):
                    d = "0.00"
                elif not d: d = "0.0"
                w.insert(0, d)

    def _export_report(self):
        if self._current_result is None:
            messagebox.showinfo("No Data", "Run analysis first."); return
        p = filedialog.asksaveasfilename(defaultextension=".md",
                                         filetypes=[("Markdown","*.md"),("JSON","*.json")])
        if not p: return
        r = self._current_result
        if p.endswith(".json"):
            out = {"player":r.player.name,"position":r.player.position.value,
                   "level":r.player.competition_level.value,"overall_score":r.overall_score,
                   "weaknesses":[{"category":w.category,"severity":w.severity,
                                  "player_value":w.player_value,"benchmark_min":w.benchmark_min,
                                  "benchmark_target":w.benchmark_target,
                                  "recommendation":w.recommendation} for w in r.weaknesses],
                   "strengths":r.strengths}
            with open(p,"w") as f: json.dump(out, f, indent=2)
        else:
            lines = [f"# {r.player.name} — Weakness Report","",
                     f"**Position:** {r.player.position.value} | **Score:** {r.overall_score:.0%}","",
                     "| # | Category | Value | Benchmark | Severity | Recommendation |",
                     "|---|----------|-------|-----------|----------|----------------|"]
            for i, w in enumerate(r.weaknesses, 1):
                lines.append(f"| {i} | {w.category} | {w.player_value:.1f} | "
                             f"{w.benchmark_min:.2f}→{w.benchmark_target:.2f} | "
                             f"{w.severity:.0%} | {w.recommendation} |")
            lines += ["","## Strengths",""] + [f"- {s}" for s in r.strengths]
            with open(p,"w") as f: f.write("\n".join(lines))
        messagebox.showinfo("Done", f"Saved to:\n{p}")

    def _add_compare(self):
        if self._current_result is None:
            messagebox.showinfo("No Data", "Run analysis first."); return
        if len(self._compare) < 2:
            self._compare.append(self._current_result)
            self._refresh_compare()
        if len(self._compare) == 2:
            messagebox.showinfo("Ready", "Both players loaded in Compare tab.")

    # ════════════════════════════════════════════════════════════
    #  VIDEO TAB
    # ════════════════════════════════════════════════════════════

    def _build_video_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  🎬 Video  ")

        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Player
        vf = ttk.Frame(pw, style="Card.TFrame")
        pw.add(vf, weight=68)

        self._vid_canvas = tk.Canvas(vf, bg="#000", highlightthickness=0)
        self._vid_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))
        self._vid_canvas.bind("<Button-1>", self._on_video_click)

        # Slider
        self._vid_slider = ttk.Scale(vf, from_=0, to=100, command=self._on_slider)
        self._vid_slider.pack(fill=tk.X, padx=10, pady=(2, 2))

        # Controls
        ctrl = ttk.Frame(vf, style="Card.TFrame")
        ctrl.pack(fill=tk.X, padx=10, pady=(2, 2))
        for txt, cmd in [("⏮ -10f", lambda: self._vid_seek_delta(-10)),
                         ("⏪ -1f", lambda: self._vid_seek_delta(-1)),
                         ("▶/⏸", self._vid_toggle_pause),
                         ("⏩ +1f", lambda: self._vid_seek_delta(1)),
                         ("⏭ +10f", lambda: self._vid_seek_delta(10))]:
            ttk.Button(ctrl, text=txt, command=cmd).pack(side=tk.LEFT, padx=2)

        self._vid_speed_var = tk.StringVar(value="1.0")
        ttk.Combobox(ctrl, textvariable=self._vid_speed_var, values=["0.25","0.5","1.0","2.0"],
                     width=5, state="readonly").pack(side=tk.RIGHT, padx=4)
        self._vid_speed_var.trace("w", lambda *a: self._on_speed_change())
        ttk.Label(ctrl, text="Speed:", font=(FONT, 10)).pack(side=tk.RIGHT)

        self._vid_info = ttk.Label(vf, text="No video loaded. Click 'Load Video…' to begin.",
                                   font=(FONT, 10), foreground=C["subtext"])
        self._vid_info.pack(fill=tk.X, padx=10, pady=(2, 6))

        # Sidebar
        sf = ttk.Frame(pw, style="Card.TFrame")
        pw.add(sf, weight=32)
        ttk.Label(sf, text="Shot Tracking", style="Heading.TLabel").pack(padx=14, pady=(14, 8))

        self._shot_counter_var = tk.StringVar(value="Shots: 0M / 0X")
        tk.Label(sf, textvariable=self._shot_counter_var, font=(FONT, 16, "bold"),
                 fg=C["text"], bg=C["card"]).pack(pady=4)

        for txt, cmd, color in [
            ("✅ Mark MAKE", lambda: self._mark_shot("make"), C["green"]),
            ("❌ Mark MISS", lambda: self._mark_shot("miss"), C["red"]),
            ("📍 Mark Arc Point", lambda: self._mark_arc(), C["orange"]),
            ("↩ Undo Last Shot", self._undo_shot, C["subtext"]),
        ]:
            btn = tk.Button(sf, text=txt, command=cmd, font=(FONT, 11), bg=color,
                            fg="#fff", activebackground=color, relief=tk.FLAT,
                            cursor="hand2", padx=10, pady=4)
            btn.pack(fill=tk.X, padx=14, pady=3)

        ttk.Separator(sf, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=14, pady=10)

        self._vid_report_text = tk.Text(sf, height=10, wrap=tk.WORD, font=(FONT, 10),
                                        bg=C["card"], fg=C["text"], relief=tk.FLAT,
                                        border=0, padx=8, pady=6)
        self._vid_report_text.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 4))

        bb = ttk.Frame(sf, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=14, pady=(4, 10))
        ttk.Button(bb, text="Load Video…", command=self._load_video).pack(side=tk.LEFT, padx=2)
        ttk.Button(bb, text="Refresh Report", command=self._vid_refresh_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(bb, text="Export Analysis", command=self._export_video_analysis).pack(side=tk.LEFT, padx=2)

    def _load_video(self):
        p = filedialog.askopenfilename(filetypes=[("Video files","*.mp4 *.mov *.avi *.mkv"),("All","*.*")])
        if not p: return
        self._stop_video_playback()
        a = self.video_analyzer.load(p)
        if a is None:
            messagebox.showerror("Error", f"Cannot open:\n{p}"); return
        self._vid_info.configure(text=f"{a.path.name} | {a.duration:.1f}s | "
                                      f"{a.resolution[0]}x{a.resolution[1]} | {a.fps:.1f}fps")
        self._vid_slider.configure(to=a.frame_count - 1)
        self._vid_slider.set(0)
        self._update_shot_counter()
        self._vid_playback_loop()

    def _vid_playback_loop(self):
        self._stop_video_playback()
        def _loop():
            if self.video_analyzer.analysis is None: return
            if not self.video_analyzer.paused:
                self.video_analyzer.get_frame()
                self.video_analyzer._current_frame_idx += 1
                if self.video_analyzer.analysis and \
                   self.video_analyzer._current_frame_idx >= self.video_analyzer.analysis.frame_count:
                    self.video_analyzer._current_frame_idx = 0
                self._vid_slider.set(self.video_analyzer._current_frame_idx)
            self._render_video_frame()
            delay = int(1000 / max(self.video_analyzer.analysis.fps, 1) / self.video_analyzer.playback_speed)
            self._video_playback_job = self.after(max(delay, 16), _loop)
        _loop()

    def _stop_video_playback(self):
        if self._video_playback_job:
            self.after_cancel(self._video_playback_job)
            self._video_playback_job = None

    def _render_video_frame(self):
        frame = self.video_analyzer.get_annotated_frame()
        if frame is None: return
        cw = self._vid_canvas.winfo_width()
        ch = self._vid_canvas.winfo_height()
        if cw < 10 or ch < 10: return
        h, w = frame.shape[:2]
        scale = min(cw/w, ch/h)
        nw, nh = int(w*scale), int(h*scale)
        img = Image.fromarray(frame).resize((nw, nh), Image.LANCZOS)
        self._vid_photo = ImageTk.PhotoImage(img)
        self._vid_canvas.delete("all")
        self._vid_canvas.create_image(cw//2, ch//2, image=self._vid_photo)

    def _on_slider(self, val):
        f = int(float(val))
        if self.video_analyzer.analysis:
            self.video_analyzer.seek(f)

    def _vid_seek_delta(self, d):
        self.video_analyzer.seek_relative(d)
        if self.video_analyzer.analysis:
            self._vid_slider.set(self.video_analyzer.current_frame_idx)
        self._render_video_frame()

    def _vid_toggle_pause(self):
        self.video_analyzer.toggle_pause()

    def _on_speed_change(self):
        try:
            self.video_analyzer.set_playback_speed(float(self._vid_speed_var.get()))
        except ValueError: pass

    def _on_video_click(self, evt):
        if self.video_analyzer.analysis is None: return
        cw = self._vid_canvas.winfo_width()
        ch = self._vid_canvas.winfo_height()
        h, w = self.video_analyzer.analysis.resolution
        scale = min(cw/w, ch/h)
        ox = (cw - w*scale)/2
        oy = (ch - h*scale)/2
        nx = (evt.x - ox) / (w*scale)
        ny = (evt.y - oy) / (h*scale)
        self._click_pos = (max(0, min(nx, 1)), max(0, min(ny, 1)))

    def _mark_shot(self, result):
        bp = getattr(self, "_click_pos", None)
        self.video_analyzer.mark_shot(result, bp)
        self._update_shot_counter()

    def _mark_arc(self):
        bp = getattr(self, "_click_pos", None)
        if bp:
            self.video_analyzer.mark_arc_point(bp)
        if self.video_analyzer.analysis and self.video_analyzer.analysis.shots:
            idx = len(self.video_analyzer.analysis.shots) - 1
            self.video_analyzer.estimate_release_angle(idx)

    def _undo_shot(self):
        self.video_analyzer.undo_last_shot()
        self._update_shot_counter()

    def _update_shot_counter(self):
        a = self.video_analyzer.analysis
        if a:
            self._shot_counter_var.set(f"Shots: {a.makes}M / {a.misses}X")

    def _vid_refresh_report(self):
        a = self.video_analyzer.analysis
        if a is None: return
        r = self.video_analyzer.get_consistency_report()
        self._vid_report_text.delete("1.0", tk.END)
        lines = []
        if "shooting_grade" in r:
            lines.append(f"Grade: {r['shooting_grade']}")
        if r.get("total_shots", 0) > 0:
            lines.append(f"FG%: {r['make_pct']:.0%} ({r['makes']}/{r['total_shots']})")
        if r.get("avg_release_angle"):
            lines.append(f"Avg Angle: {r['avg_release_angle']:.1f}° ({r.get('angle_grade', 'N/A')})")
        if r.get("angle_consistency_std") is not None:
            lines.append(f"Consistency: σ={r['angle_consistency_std']:.1f}° ({r.get('consistency_grade', 'N/A')})")
        self._vid_report_text.insert("1.0", "\n".join(lines) if lines else "Mark shots to see report.")

    def _export_video_analysis(self):
        if self.video_analyzer.analysis is None:
            messagebox.showinfo("No Data", "Load and analyze a video first."); return
        p = filedialog.asksaveasfilename(defaultextension=".json",
                                         filetypes=[("JSON","*.json")])
        if not p: return
        self.video_analyzer.export_analysis(p)
        messagebox.showinfo("Done", f"Saved to:\n{p}")

    # ════════════════════════════════════════════════════════════
    #  CAMERA TAB
    # ════════════════════════════════════════════════════════════

    def _build_camera_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  📷 Camera  ")

        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        vf = ttk.Frame(pw, style="Card.TFrame")
        pw.add(vf, weight=65)
        self._cam_canvas = tk.Canvas(vf, bg="#000", highlightthickness=0)
        self._cam_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ctrl = ttk.Frame(vf, style="Card.TFrame")
        ctrl.pack(fill=tk.X, padx=10, pady=(0, 10))
        self._cam_status = ttk.Label(ctrl, text="Camera: Off", foreground=C["subtext"])
        self._cam_status.pack(side=tk.LEFT, padx=4)
        self._cam_rec_btn = ttk.Button(ctrl, text="🔴 Start Recording", command=self._cam_toggle_rec)
        self._cam_rec_btn.pack(side=tk.RIGHT, padx=4)
        ttk.Button(ctrl, text="📷 Open Camera", command=self._cam_open).pack(side=tk.RIGHT, padx=4)
        ttk.Button(ctrl, text="🔄 Refresh", command=self._cam_refresh).pack(side=tk.RIGHT, padx=4)

        self._cam_timer_var = tk.StringVar(value="")
        tk.Label(vf, textvariable=self._cam_timer_var, font=(FONT, 14, "bold"),
                 fg=C["red"], bg=C["card"]).pack(pady=(0, 6))

        # Recordings list
        sf = ttk.Frame(pw, style="Card.TFrame")
        pw.add(sf, weight=35)
        ttk.Label(sf, text="Recordings", style="Heading.TLabel").pack(padx=14, pady=(14, 8))

        self._rec_list = tk.Listbox(sf, bg=C["entry_bg"], fg=C["text"], font=(FONT, 11),
                                    relief=tk.FLAT, border=0, selectbackground=C["accent"],
                                    selectforeground="#fff")
        self._rec_list.pack(fill=tk.BOTH, expand=True, padx=14, pady=4)
        self._rec_list.bind("<Double-1>", lambda e: self._cam_play_recording())

        bb = ttk.Frame(sf, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=14, pady=(6, 10))
        ttk.Button(bb, text="▶ Play Selected", command=self._cam_play_recording).pack(side=tk.LEFT, padx=2)
        ttk.Button(bb, text="🗑 Clear List", command=self._cam_clear_list).pack(side=tk.LEFT, padx=2)

        self._cam_tips = tk.Text(sf, height=6, wrap=tk.WORD, font=(FONT, 10),
                                 bg=C["card"], fg=C["subtext"], relief=tk.FLAT,
                                 border=0, padx=8, pady=6)
        self._cam_tips.insert("1.0",
            "Tips for recording:\n\n"
            "• Position camera to see full shot motion\n"
            "• Ensure good lighting\n"
            "• Record 10-20 shots per session\n"
            "• After recording, load video in Video tab\n"
            "  to mark shots and analyze form")
        self._cam_tips.configure(state=tk.DISABLED)
        self._cam_tips.pack(fill=tk.X, padx=14, pady=(0, 10))

    def _cam_open(self):
        if self.camera.is_open:
            self._cam_close()
        ok = self.camera.open(0)
        if ok:
            self._cam_status.configure(text="Camera: Live", foreground=C["green"])
            self._cam_preview_loop()
        else:
            self._cam_status.configure(text="Camera: Error — check connection", foreground=C["red"])

    def _cam_close(self):
        self._stop_cam_preview()
        self.camera.close()
        self._cam_status.configure(text="Camera: Off", foreground=C["subtext"])
        self._cam_canvas.delete("all")

    def _cam_preview_loop(self):
        self._stop_cam_preview()
        def _loop():
            if not self.camera.is_open: return
            frame = self.camera.preview_frame()
            if frame is not None:
                cw = self._cam_canvas.winfo_width()
                ch = self._cam_canvas.winfo_height()
                if cw>10 and ch>10:
                    h, w = frame.shape[:2]
                    scale = min(cw/w, ch/h)
                    nw, nh = int(w*scale), int(h*scale)
                    img = Image.fromarray(frame).resize((nw, nh), Image.LANCZOS)
                    self._cam_photo = ImageTk.PhotoImage(img)
                    self._cam_canvas.delete("all")
                    self._cam_canvas.create_image(cw//2, ch//2, image=self._cam_photo)
            if self.camera.is_recording:
                self.camera.write_frame(frame)
                elapsed = time.time() - self.camera._start_time
                self._cam_timer_var.set(f"🔴 RECORDING — {elapsed:.0f}s")
            self._cam_preview_job = self.after(33, _loop)
        _loop()

    def _stop_cam_preview(self):
        if self._cam_preview_job:
            self.after_cancel(self._cam_preview_job)
            self._cam_preview_job = None

    def _cam_toggle_rec(self):
        if not self.camera.is_open:
            messagebox.showinfo("No Camera", "Open camera first."); return
        if self.camera.is_recording:
            rec = self.camera.stop_recording()
            self._cam_rec_btn.configure(text="🔴 Start Recording")
            self._cam_timer_var.set("")
            if rec:
                self._rec_list.insert(0, f"{rec.path.name} ({rec.duration:.1f}s)")
        else:
            ok = self.camera.start_recording(str(Path.home() / "Desktop"))
            if ok:
                self._cam_rec_btn.configure(text="⏹ Stop Recording")
            else:
                messagebox.showerror("Error", "Could not start recording.")

    def _cam_refresh(self):
        if self.camera.is_open:
            self._stop_cam_preview()
            self._cam_preview_loop()

    def _cam_clear_list(self):
        self._rec_list.delete(0, tk.END)

    def _cam_play_recording(self):
        sel = self._rec_list.curselection()
        if not sel: return
        name = self._rec_list.get(sel[0]).split(" (")[0]
        path = str(Path.home() / "Desktop" / name)
        if Path(path).exists():
            self._stop_cam_preview()
            self._stop_video_playback()
            self.video_analyzer.close()
            a = self.video_analyzer.load(path)
            if a:
                self.notebook.select(1)  # Switch to Video tab
                self._vid_info.configure(text=f"{a.path.name} | {a.duration:.1f}s | "
                                              f"{a.resolution[0]}x{a.resolution[1]}")
                self._vid_slider.configure(to=a.frame_count - 1)
                self._vid_slider.set(0)
                self._vid_playback_loop()

    # ════════════════════════════════════════════════════════════
    #  COMPARE TAB
    # ════════════════════════════════════════════════════════════

    def _build_compare_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  ⚖ Compare  ")
        self._compare_text = tk.Text(tab, wrap=tk.WORD, font=(FONT, 13),
                                     bg=C["card"], fg=C["text"], relief=tk.FLAT,
                                     border=0, padx=20, pady=20, state=tk.DISABLED)
        self._compare_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._compare_text.tag_configure("h1", font=(FONT, 18, "bold"), foreground=C["text"])
        self._compare_text.tag_configure("h2", font=(FONT, 13, "bold"), foreground=C["text"])
        self._compare_text.tag_configure("g", foreground=C["green"])
        self._compare_text.tag_configure("r", foreground=C["red"])
        self._compare_text.tag_configure("o", foreground=C["orange"])
        self._compare_text.tag_configure("n", foreground=C["text"])
        bb = ttk.Frame(tab, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(bb, text="Clear", command=self._clear_compare).pack(side=tk.LEFT, padx=4)

    def _refresh_compare(self):
        self._compare_text.configure(state=tk.NORMAL)
        self._compare_text.delete("1.0", tk.END)
        if len(self._compare) == 0:
            self._compare_text.insert("1.0", "Add players from Analyze tab.\n", "n")
        elif len(self._compare) == 1:
            r = self._compare[0]
            self._compare_text.insert("1.0", f"Player 1: {r.player.name}\nAdd another to compare.\n", "n")
        else:
            r1, r2 = self._compare
            self._compare_text.insert("1.0", f"{r1.player.name}  vs  {r2.player.name}\n", "h1")
            self._compare_text.insert(tk.END, f"{'='*55}\n\n", "n")
            self._compare_text.insert(tk.END,
                f"{'Category':<26} {r1.player.name:<16} {r2.player.name:<16}\n", "h2")
            self._compare_text.insert(tk.END, f"{'-'*58}\n", "n")
            cats = set()
            for w in r1.weaknesses + r2.weaknesses: cats.add(w.category)
            for cat in sorted(cats):
                w1 = next((w for w in r1.weaknesses if w.category==cat), None)
                w2 = next((w for w in r2.weaknesses if w.category==cat), None)
                t1 = "g" if w1 is None else ("r" if w1.severity>0.5 else "o" if w1.severity>0.25 else "g")
                t2 = "g" if w2 is None else ("r" if w2.severity>0.5 else "o" if w2.severity>0.25 else "g")
                s1 = f"{w1.severity:.0%}" if w1 else "✓"
                s2 = f"{w2.severity:.0%}" if w2 else "✓"
                self._compare_text.insert(tk.END, f"{cat:<26} ", "n")
                self._compare_text.insert(tk.END, f"{s1:<16}", t1)
                self._compare_text.insert(tk.END, f" {s2:<16}\n", t2)
            self._compare_text.insert(tk.END, "\n", "n")
            if r1.weaknesses:
                self._compare_text.insert(tk.END,
                    f"🔴 {r1.player.name}: {r1.weaknesses[0].category}\n", "r")
            if r2.weaknesses:
                self._compare_text.insert(tk.END,
                    f"🔴 {r2.player.name}: {r2.weaknesses[0].category}\n", "r")
        self._compare_text.configure(state=tk.DISABLED)

    def _clear_compare(self):
        self._compare.clear()
        self._refresh_compare()

    # ════════════════════════════════════════════════════════════
    #  HISTORY TAB
    # ════════════════════════════════════════════════════════════

    def _build_history_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  📋 History  ")
        self._hist_tree = ttk.Treeview(tab, columns=("player","pos","score","date"),
                                       show="headings", height=14)
        for c, w in [("player", 200), ("pos", 130), ("score", 80), ("date", 150)]:
            self._hist_tree.heading(c, text=c.title())
            self._hist_tree.column(c, width=w)
        self._hist_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        bb = ttk.Frame(tab, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(bb, text="Clear History", command=self._clear_history).pack(side=tk.LEFT, padx=4)

    def _save_history(self, r):
        from datetime import datetime
        ds = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._history.append(r)
        self._hist_tree.insert("", 0, values=(r.player.name, r.player.position.value,
                                               f"{r.overall_score:.0%}", ds))

    def _clear_history(self):
        self._history.clear()
        for i in self._hist_tree.get_children():
            self._hist_tree.delete(i)

    # ── Cleanup ────────────────────────────────────────────────

    def destroy(self):
        self._stop_cam_preview()
        self._stop_video_playback()
        self.camera.close()
        self.video_analyzer.close()
        super().destroy()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
