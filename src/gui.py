"""Basketball Inability Analyzer — macOS GUI (fast startup, lazy imports)."""

from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Light imports — everything heavy is loaded on demand
from src.models import Player, GameStats, Position, CompetitionLevel
from src.analyzer import WeaknessAnalyzer

# ── Theme ──────────────────────────────────────────────────────
C = {
    "bg":       "#0b0b1a",  "card":     "#14142b",  "card2": "#1e1e3a",
    "accent":   "#ff5e5b",  "accent2":  "#6c5ce7",  "green":  "#00d2a0",
    "orange":   "#ffa502",  "red":      "#ff4757",   "blue":   "#4d8af0",
    "text":     "#eef0f6",  "subtext":  "#8b8daa",   "border": "#25254a",
    "entry_bg": "#0d0d24",
}
F = "Helvetica Neue"


# ── Lazy-load helpers ──────────────────────────────────────────

def _lazy_camera():
    from src.camera import CameraManager
    return CameraManager

def _lazy_video_analyzer():
    from src.video_analyzer import VideoAnalyzer
    return VideoAnalyzer

def _lazy_config():
    import src.config as m
    return m

def _lazy_ai():
    import src.ai_analyzer as m
    return m

def _lazy_pil():
    from PIL import Image, ImageTk
    return Image, ImageTk


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Basketball Inability Analyzer")
        self.geometry("1150x800")
        self.minsize(960, 640)
        self.configure(bg=C["bg"])

        self.analyzer = WeaknessAnalyzer()
        self._camera = None
        self._video = None
        self._cam_job: str | None = None
        self._vid_job: str | None = None
        self._current_result = None
        self._compare: list = []
        self._click_pos: tuple[float, float] | None = None

        self._setup_style()
        self._build()

    @property
    def camera(self):
        if self._camera is None:
            try:
                self._camera = _lazy_camera()()
            except Exception as e:
                messagebox.showerror("Camera Error",
                    f"Could not load camera module.\n\n{str(e)}\n\n"
                    "Make sure OpenCV is installed:\npip install opencv-python")
                raise
        return self._camera

    @property
    def video(self):
        if self._video is None:
            try:
                self._video = _lazy_video_analyzer()()
            except Exception as e:
                messagebox.showerror("Video Error",
                    f"Could not load video module.\n\n{str(e)}")
                raise
        return self._video

    # ── Style (minimal, fast) ─────────────────────────────────

    def _setup_style(self):
        s = ttk.Style()
        s.configure(".", background=C["bg"], foreground=C["text"], font=(F, 11))
        s.configure("TNotebook", background=C["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", padding=[16, 8], font=(F, 12, "bold"),
                     background=C["card"], foreground=C["subtext"], borderwidth=0)
        try:
            s.map("TNotebook.Tab",
                  background=[("selected", C["accent"]), ("active", C["card2"])],
                  foreground=[("selected", "#fff"), ("active", C["text"])])
        except tk.TclError:
            pass
        for name, bg in [("Card.TFrame", C["card"]), ("Dark.TFrame", C["bg"])]:
            s.configure(name, background=bg)
        s.configure("Title.TLabel", font=(F, 18, "bold"), foreground=C["text"], background=C["bg"])
        s.configure("Heading.TLabel", font=(F, 14, "bold"), foreground=C["text"], background=C["card"])
        s.configure("Sub.TLabel", font=(F, 11), foreground=C["subtext"], background=C["card"])
        s.configure("TLabel", background=C["card"], foreground=C["text"], font=(F, 11))
        s.configure("TEntry", fieldbackground=C["entry_bg"], foreground=C["text"])
        s.configure("TSeparator", background=C["border"])

    # ── Build ──────────────────────────────────────────────────

    def _build(self):
        bar = ttk.Frame(self, style="Dark.TFrame")
        bar.pack(fill=tk.X, padx=24, pady=(14, 4))
        ttk.Label(bar, text="🏀  Basketball Analyzer", style="Title.TLabel").pack(side=tk.LEFT)
        self._status_lbl = ttk.Label(bar, text="Ready", foreground=C["subtext"],
                                     background=C["bg"], font=(F, 10))
        self._status_lbl.pack(side=tk.RIGHT, pady=(6, 0))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=14, pady=(2, 14))

        self._build_analyze()
        self._build_video()
        self._build_camera()
        self._build_ai_coach()
        self._build_compare()
        self._build_history()

    # ════════════════════════════════════════════════════════════
    #  TAB 1: ANALYZE (built at startup — lightweight)
    # ════════════════════════════════════════════════════════════

    def _build_analyze(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="  📊 Analyze  ")
        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = ttk.Frame(pw, style="Card.TFrame")
        pw.add(left, weight=40)
        right = ttk.Frame(pw, style="Card.TFrame")
        pw.add(right, weight=60)
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
        for w in (cv, sf):
            w.bind("<MouseWheel>", lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"))

        p = {"padx": 14, "pady": 3, "sticky": "w"}
        self.fields: dict[str, tk.Widget] = {}

        ttk.Label(sf, text="👤 Player Info", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, padx=14, pady=(14, 8), sticky="w")
        for r, (k, lbl, default) in enumerate([
            ("name", "Name", ""), ("position", "Position", "Shooting Guard"),
            ("level", "Level", "high_school"), ("games_played", "Games", "20"),
            ("minutes_per_game", "Min/Game", "28"),
        ], 1):
            ttk.Label(sf, text=lbl).grid(row=r, column=0, **p)
            if k == "position":
                w = ttk.Combobox(sf, values=[p.value for p in Position], state="readonly", width=22)
                w.set(default)
            elif k == "level":
                w = ttk.Combobox(sf, values=[l.value for l in CompetitionLevel], state="readonly", width=22)
                w.set(default)
            else:
                w = ttk.Entry(sf, width=24)
                if default: w.insert(0, default)
            w.grid(row=r, column=1, **p)
            self.fields[k] = w

        ttk.Label(sf, text="📊 Per-Game Averages", style="Heading.TLabel").grid(
            row=7, column=0, columnspan=2, padx=14, pady=(16, 8), sticky="w")
        for i, (k, lbl) in enumerate([
            ("points_per_game", "PPG"), ("assists_per_game", "APG"),
            ("rebounds_per_game", "RPG"), ("steals_per_game", "SPG"),
            ("blocks_per_game", "BPG"), ("turnovers_per_game", "TO"),
        ]):
            ttk.Label(sf, text=lbl).grid(row=8+i, column=0, **p)
            w = ttk.Entry(sf, width=24); w.insert(0, "0.0")
            w.grid(row=8+i, column=1, **p)
            self.fields[k] = w

        ttk.Label(sf, text="🎯 Shooting %", style="Heading.TLabel").grid(
            row=15, column=0, columnspan=2, padx=14, pady=(16, 8), sticky="w")
        for i, (k, lbl) in enumerate([
            ("field_goal_pct", "FG% (0.42)"), ("three_point_pct", "3P% (0.35)"),
            ("free_throw_pct", "FT% (0.72)"),
        ]):
            ttk.Label(sf, text=lbl).grid(row=16+i, column=0, **p)
            w = ttk.Entry(sf, width=24); w.insert(0, "0.00")
            w.grid(row=16+i, column=1, **p)
            self.fields[k] = w

        bf = ttk.Frame(sf, style="Card.TFrame")
        bf.grid(row=20, column=0, columnspan=2, pady=(16, 14), padx=14)
        tk.Button(bf, text="🔍 Analyze", font=(F, 12, "bold"),
                  bg=C["accent"], fg="#fff", activebackground=C["red"],
                  relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                  command=self._run_analysis).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text="Load JSON…", command=self._load_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text="Clear", command=self._clear_form).pack(side=tk.LEFT, padx=2)

    def _build_result(self, parent):
        hdr = ttk.Frame(parent, style="Card.TFrame")
        hdr.pack(fill=tk.X, padx=16, pady=(14, 6))
        self._result_title = ttk.Label(hdr, text="Analysis", style="Heading.TLabel")
        self._result_title.pack(side=tk.LEFT)
        self._score_lbl = tk.Label(hdr, text="—", font=(F, 34, "bold"),
                                   fg=C["accent"], bg=C["card"])
        self._score_lbl.pack(side=tk.RIGHT)

        self._summary_lbl = ttk.Label(parent, text="Fill in your stats and click Analyze.",
                                      wraplength=480, foreground=C["subtext"])
        self._summary_lbl.pack(fill=tk.X, padx=16, pady=(0, 6))
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16)

        self._result_tree = ttk.Treeview(parent, columns=("r","cat","val","bench","sev"),
                                         show="headings", height=9)
        for c, w, a in [("r", 30, "center"), ("cat", 155, "w"), ("val", 60, "center"),
                         ("bench", 120, "center"), ("sev", 85, "center")]:
            self._result_tree.heading(c, text={"r":"#","cat":"Category","val":"Value",
                                               "bench":"Benchmark","sev":"Severity"}[c])
            self._result_tree.column(c, width=w, anchor=a)
        self._result_tree.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        self._rec_text = tk.Text(parent, height=4, wrap=tk.WORD, font=(F, 11),
                                 bg=C["card"], fg=C["text"], relief=tk.FLAT, border=0,
                                 padx=8, pady=6, state=tk.DISABLED)
        self._rec_text.tag_configure("b", font=(F, 11, "bold"), foreground=C["accent"])
        self._rec_text.tag_configure("r", foreground=C["subtext"])
        self._rec_text.pack(fill=tk.X, padx=16, pady=(0, 4))

        bb = ttk.Frame(parent, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=16, pady=(2, 10))
        ttk.Button(bb, text="Export", command=self._export_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(bb, text="Add to Compare", command=self._add_compare).pack(side=tk.LEFT, padx=2)

    # ── Analyze actions ────────────────────────────────────────

    def _read_form(self) -> Player | None:
        try:
            name = self.fields["name"].get().strip() or "Player"
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
            messagebox.showerror("Check Input", f"Please fill all fields correctly.\n{str(e)}")
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
            self._result_tree.insert("", tk.END, values=(i, w.category, vs, bs, f"{w.severity:.0%}"),
                                     tags=(tag,))
            if w.severity > 0.5: self._result_tree.tag_configure(tag, foreground=C["red"])
            elif w.severity > 0.25: self._result_tree.tag_configure(tag, foreground=C["orange"])
        self._rec_text.configure(state=tk.NORMAL)
        self._rec_text.delete("1.0", tk.END)
        if r.weaknesses:
            self._rec_text.insert("1.0", f"🎯 Top: {r.weaknesses[0].category}\n", "b")
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
            pm = {pp.name: pp.value for pp in Position}
            self.fields["position"].set(pm.get(data.get("position","SG"), "Shooting Guard"))
            self.fields["level"].set(data.get("competition_level","high_school"))
            for k in ["games_played","minutes_per_game","points_per_game","assists_per_game",
                      "rebounds_per_game","steals_per_game","blocks_per_game","turnovers_per_game",
                      "field_goal_pct","three_point_pct","free_throw_pct"]:
                if k in data and k in self.fields:
                    self.fields[k].delete(0, tk.END); self.fields[k].insert(0, str(data[k]))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _clear_form(self):
        for k, w in self.fields.items():
            if isinstance(w, ttk.Entry):
                w.delete(0, tk.END)
                d = {"games_played":"20","minutes_per_game":"28"}.get(k, "")
                if "pct" in k: d = "0.00"
                elif not d: d = "0.0"
                w.insert(0, d)

    def _export_report(self):
        if self._current_result is None:
            messagebox.showinfo("Nothing", "Run analysis first."); return
        p = filedialog.asksaveasfilename(defaultextension=".md",
                                         filetypes=[("Markdown","*.md"),("JSON","*.json")])
        if not p: return
        r = self._current_result
        if p.endswith(".json"):
            out = {"player":r.player.name,"position":r.player.position.value,
                   "level":r.player.competition_level.value,"overall_score":r.overall_score,
                   "weaknesses":[{"category":w.category,"severity":w.severity,
                                  "value":w.player_value,"recommendation":w.recommendation}
                                 for w in r.weaknesses],
                   "strengths":r.strengths}
            with open(p,"w") as f: json.dump(out, f, indent=2)
        else:
            lines = [f"# {r.player.name} — Weakness Report","",
                     f"**Pos:** {r.player.position.value} | **Score:** {r.overall_score:.0%}","",
                     "| # | Category | Value | Benchmark | Severity | Recommendation |",
                     "|---|----------|-------|-----------|----------|----------------|"]
            for i, w in enumerate(r.weaknesses, 1):
                lines.append(f"| {i} | {w.category} | {w.player_value:.1f} | "
                             f"{w.benchmark_min:.2f}→{w.benchmark_target:.2f} | "
                             f"{w.severity:.0%} | {w.recommendation} |")
            lines += ["","## Strengths",""] + [f"- {s}" for s in r.strengths]
            with open(p,"w") as f: f.write("\n".join(lines))
        messagebox.showinfo("Done", f"Saved:\n{p}")

    def _add_compare(self):
        if self._current_result is None:
            messagebox.showinfo("Nothing", "Run analysis first."); return
        if len(self._compare) < 2:
            self._compare.append(self._current_result)
            # Ensure compare tab is built
            self._refresh_compare()

    # ════════════════════════════════════════════════════════════
    #  TAB 2: VIDEO (lazy)
    # ════════════════════════════════════════════════════════════

    def _build_video(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="  🎬 Video  ")
        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        vf = ttk.Frame(pw, style="Card.TFrame")
        pw.add(vf, weight=68)
        self._vid_canvas = tk.Canvas(vf, bg="#000", highlightthickness=0)
        self._vid_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))
        self._vid_canvas.bind("<Button-1>", self._on_video_click)

        self._vid_slider = ttk.Scale(vf, from_=0, to=100, command=self._on_slider)
        self._vid_slider.pack(fill=tk.X, padx=10, pady=(2, 2))

        ctrl = ttk.Frame(vf, style="Card.TFrame")
        ctrl.pack(fill=tk.X, padx=10, pady=(2, 2))
        for txt, cmd in [("⏮ -10f", lambda: self._vid_seek(-10)),
                         ("-1f", lambda: self._vid_seek(-1)),
                         ("▶⏸", self._vid_toggle_pause),
                         ("+1f", lambda: self._vid_seek(1)),
                         ("⏭ +10f", lambda: self._vid_seek(10))]:
            ttk.Button(ctrl, text=txt, command=cmd).pack(side=tk.LEFT, padx=1)
        self._vid_speed_var = tk.StringVar(value="1.0")
        ttk.Combobox(ctrl, textvariable=self._vid_speed_var, values=["0.25","0.5","1.0","2.0"],
                     width=4, state="readonly").pack(side=tk.RIGHT, padx=4)
        self._vid_speed_var.trace("w", lambda *a: self._on_speed_change())
        ttk.Label(ctrl, text="Speed:", font=(F, 10)).pack(side=tk.RIGHT)

        self._vid_info = ttk.Label(vf, text="No video loaded. Click 'Load Video…'",
                                   font=(F, 10), foreground=C["subtext"])
        self._vid_info.pack(fill=tk.X, padx=10, pady=(2, 6))

        # Sidebar
        sf = ttk.Frame(pw, style="Card.TFrame")
        pw.add(sf, weight=32)
        ttk.Label(sf, text="🎯 Shot Tracking", style="Heading.TLabel").pack(padx=14, pady=(14, 8))
        self._shot_counter_var = tk.StringVar(value="Shots: 0M / 0X")
        tk.Label(sf, textvariable=self._shot_counter_var, font=(F, 16, "bold"),
                 fg=C["text"], bg=C["card"]).pack(pady=4)
        for txt, cmd, color in [
            ("✅ MAKE", lambda: self._mark_shot("make"), C["green"]),
            ("❌ MISS", lambda: self._mark_shot("miss"), C["red"]),
            ("📍 Arc Point", self._mark_arc, C["orange"]),
            ("↩ Undo", self._undo_shot, C["subtext"]),
        ]:
            tk.Button(sf, text=txt, command=cmd, font=(F, 11), bg=color, fg="#fff",
                      relief=tk.FLAT, cursor="hand2", padx=10, pady=4
                      ).pack(fill=tk.X, padx=14, pady=2)
        ttk.Separator(sf, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=14, pady=8)
        self._vid_report_text = tk.Text(sf, height=8, wrap=tk.WORD, font=(F, 10),
                                        bg=C["card"], fg=C["text"], relief=tk.FLAT,
                                        border=0, padx=8, pady=6)
        self._vid_report_text.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 4))
        bb = ttk.Frame(sf, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=14, pady=(4, 10))
        ttk.Button(bb, text="Load Video…", command=self._load_video).pack(side=tk.LEFT, padx=2)
        ttk.Button(bb, text="Update", command=self._vid_refresh_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(bb, text="Export", command=self._export_video_analysis).pack(side=tk.LEFT, padx=2)

    def _load_video(self):
        p = filedialog.askopenfilename(filetypes=[("Video","*.mp4 *.mov *.avi *.mkv"),("All","*.*")])
        if not p: return
        self._stop_vid()
        try:
            a = self.video.load(p)
            if a is None:
                messagebox.showerror("Error", f"Cannot open:\n{p}"); return
            self._vid_info.configure(text=f"{a.path.name} | {a.duration:.1f}s | "
                                          f"{a.resolution[0]}x{a.resolution[1]}")
            self._vid_slider.configure(to=a.frame_count - 1); self._vid_slider.set(0)
            self._update_shot_counter()
            self._vid_loop()
        except Exception as e:
            messagebox.showerror("Video Error", str(e))

    def _vid_loop(self):
        self._stop_vid()
        def _l():
            try:
                if not hasattr(self, '_vid_canvas') or self.video.analysis is None: return
                if not self.video.paused:
                    self.video.get_frame()
                    self.video._current_frame_idx += 1
                    if self.video._current_frame_idx >= self.video.analysis.frame_count:
                        self.video._current_frame_idx = 0
                    self._vid_slider.set(self.video._current_frame_idx)
                self._render_video()
                delay = int(1000/max(self.video.analysis.fps,1)/max(self.video.playback_speed,0.1))
                self._vid_job = self.after(max(delay,30), _l)
            except Exception:
                pass  # Don't crash on frame errors
        _l()

    def _stop_vid(self):
        if self._vid_job:
            self.after_cancel(self._vid_job); self._vid_job = None

    def _render_video(self):
        if not hasattr(self, '_vid_canvas'): return
        frame = self.video.get_annotated_frame()
        if frame is None: return
        cw = self._vid_canvas.winfo_width(); ch = self._vid_canvas.winfo_height()
        if cw<10 or ch<10: return
        h, w = frame.shape[:2]
        scale = min(cw/w, ch/h)
        nw, nh = int(w*scale), int(h*scale)
        Image, ImageTk = _lazy_pil()
        img = Image.fromarray(frame).resize((nw, nh), Image.LANCZOS)
        self._vid_photo = ImageTk.PhotoImage(img)
        self._vid_canvas.delete("all")
        self._vid_canvas.create_image(cw//2, ch//2, image=self._vid_photo)

    def _on_slider(self, val):
        if hasattr(self, '_vid_canvas') and self.video.analysis:
            self.video.seek(int(float(val)))

    def _vid_seek(self, d):
        self.video.seek_relative(d)
        if self.video.analysis: self._vid_slider.set(self.video.current_frame_idx)
        self._render_video()

    def _vid_toggle_pause(self): self.video.toggle_pause()

    def _on_speed_change(self):
        try: self.video.set_playback_speed(float(self._vid_speed_var.get()))
        except ValueError: pass

    def _on_video_click(self, evt):
        if self.video.analysis is None: return
        cw = self._vid_canvas.winfo_width(); ch = self._vid_canvas.winfo_height()
        h, w = self.video.analysis.resolution
        scale = min(cw/w, ch/h)
        ox = (cw - w*scale)/2; oy = (ch - h*scale)/2
        if w*scale > 0 and h*scale > 0:
            self._click_pos = (max(0,min((evt.x-ox)/(w*scale),1)),
                               max(0,min((evt.y-oy)/(h*scale),1)))

    def _mark_shot(self, result):
        self.video.mark_shot(result, getattr(self, "_click_pos", None))
        self._update_shot_counter()

    def _mark_arc(self):
        bp = getattr(self, "_click_pos", None)
        if bp: self.video.mark_arc_point(bp)
        a = self.video.analysis
        if a and a.shots: self.video.estimate_release_angle(len(a.shots)-1)

    def _undo_shot(self): self.video.undo_last_shot(); self._update_shot_counter()

    def _update_shot_counter(self):
        a = self.video.analysis
        if a: self._shot_counter_var.set(f"Shots: {a.makes}M / {a.misses}X")

    def _vid_refresh_report(self):
        a = self.video.analysis
        if a is None: return
        r = self.video.get_consistency_report()
        self._vid_report_text.delete("1.0", tk.END)
        lines = []
        if "shooting_grade" in r: lines.append(f"Grade: {r['shooting_grade']}")
        if r.get("total_shots",0)>0: lines.append(f"FG%: {r['make_pct']:.0%} ({r['makes']}/{r['total_shots']})")
        if r.get("avg_release_angle"): lines.append(f"Angle: {r['avg_release_angle']:.1f}° ({r.get('angle_grade','N/A')})")
        if r.get("angle_consistency_std") is not None: lines.append(f"Consistency: {r['angle_consistency_std']:.1f}°")
        self._vid_report_text.insert("1.0", "\n".join(lines) if lines else "Mark shots first.")

    def _export_video_analysis(self):
        if self.video.analysis is None:
            messagebox.showinfo("No data", "Load and mark shots first."); return
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if not p: return
        self.video.export_analysis(p)
        messagebox.showinfo("Done", f"Saved:\n{p}")

    # ════════════════════════════════════════════════════════════
    #  TAB 3: CAMERA (lazy)
    # ════════════════════════════════════════════════════════════

    def _build_camera(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="  📷 Camera  ")
        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        vf = ttk.Frame(pw, style="Card.TFrame")
        pw.add(vf, weight=65)
        self._cam_canvas = tk.Canvas(vf, bg="#000", highlightthickness=0)
        self._cam_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        ctrl = ttk.Frame(vf, style="Card.TFrame")
        ctrl.pack(fill=tk.X, padx=10, pady=(0,10))
        self._cam_status = ttk.Label(ctrl, text="Camera: Off", foreground=C["subtext"])
        self._cam_status.pack(side=tk.LEFT, padx=4)
        self._cam_rec_btn = ttk.Button(ctrl, text="🔴 Record", command=self._cam_toggle_rec)
        self._cam_rec_btn.pack(side=tk.RIGHT, padx=4)
        ttk.Button(ctrl, text="📷 Open", command=self._cam_open).pack(side=tk.RIGHT, padx=4)
        self._cam_timer_var = tk.StringVar(value="")
        tk.Label(vf, textvariable=self._cam_timer_var, font=(F, 14, "bold"),
                 fg=C["red"], bg=C["card"]).pack(pady=(0,6))

        sf = ttk.Frame(pw, style="Card.TFrame")
        pw.add(sf, weight=35)
        ttk.Label(sf, text="🎥 Recordings", style="Heading.TLabel").pack(padx=14, pady=(14,8))
        self._rec_list = tk.Listbox(sf, bg=C["entry_bg"], fg=C["text"], font=(F,11),
                                    relief=tk.FLAT, border=0, selectbackground=C["accent"],
                                    selectforeground="#fff")
        self._rec_list.pack(fill=tk.BOTH, expand=True, padx=14, pady=4)
        self._rec_list.bind("<Double-1>", lambda e: self._cam_play_recording())
        bb = ttk.Frame(sf, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=14, pady=(6,10))
        ttk.Button(bb, text="▶ Play", command=self._cam_play_recording).pack(side=tk.LEFT, padx=2)
        ttk.Button(bb, text="🗑 Clear", command=self._cam_clear_list).pack(side=tk.LEFT, padx=2)
        tips = tk.Text(sf, height=5, wrap=tk.WORD, font=(F,10), bg=C["card"], fg=C["subtext"],
                       relief=tk.FLAT, border=0, padx=8, pady=6, state=tk.DISABLED)
        tips.insert("1.0", "💡 Record 10-20 shots, then analyze in Video tab.")
        tips.pack(fill=tk.X, padx=14, pady=(0,10))

    def _cam_open(self):
        try:
            if self.camera.is_open: self._cam_close()
            if self.camera.open(0):
                self._cam_status.configure(text="Live", foreground=C["green"])
                self._cam_loop()
            else:
                self._cam_status.configure(text="No camera found", foreground=C["red"])
        except Exception as e:
            self._cam_status.configure(text="Error", foreground=C["red"])
            messagebox.showerror("Camera Error", str(e))

    def _cam_close(self):
        self._stop_cam()
        self.camera.close()
        self._cam_status.configure(text="Off", foreground=C["subtext"])
        if hasattr(self, '_cam_canvas'): self._cam_canvas.delete("all")

    def _cam_loop(self):
        self._stop_cam()
        def _l():
            try:
                if not self.camera.is_open: return
                frame = self.camera.preview_frame()
                if frame is not None and hasattr(self, '_cam_canvas'):
                    cw=self._cam_canvas.winfo_width(); ch=self._cam_canvas.winfo_height()
                    if cw>10 and ch>10:
                        h,w=frame.shape[:2]; scale=min(cw/w,ch/h)
                        nw,nh=int(w*scale),int(h*scale)
                        Image, ImageTk = _lazy_pil()
                        img=Image.fromarray(frame).resize((nw,nh),Image.LANCZOS)
                        self._cam_photo=ImageTk.PhotoImage(img)
                        self._cam_canvas.delete("all")
                        self._cam_canvas.create_image(cw//2,ch//2,image=self._cam_photo)
                if self.camera.is_recording:
                    self.camera.write_frame(frame)
                    self._cam_timer_var.set(f"🔴 REC {time.time()-self.camera._start_time:.0f}s")
            except Exception:
                pass  # Don't crash on individual frame errors
            self._cam_job=self.after(50, _l)
        _l()

    def _stop_cam(self):
        if self._cam_job:
            self.after_cancel(self._cam_job); self._cam_job=None

    def _cam_toggle_rec(self):
        if not self.camera.is_open:
            messagebox.showinfo("No Camera", "Open camera first."); return
        if self.camera.is_recording:
            rec = self.camera.stop_recording()
            self._cam_rec_btn.configure(text="🔴 Record"); self._cam_timer_var.set("")
            if rec: self._rec_list.insert(0, f"{rec.path.name} ({rec.duration:.1f}s)")
        else:
            if self.camera.start_recording(str(Path.home()/"Desktop")):
                self._cam_rec_btn.configure(text="⏹ Stop")
            else:
                messagebox.showerror("Error", "Could not record.")

    def _cam_clear_list(self): self._rec_list.delete(0, tk.END)

    def _cam_play_recording(self):
        sel = self._rec_list.curselection()
        if not sel: return
        name = self._rec_list.get(sel[0]).split(" (")[0]
        path = str(Path.home()/"Desktop"/name)
        if Path(path).exists():
            self._stop_cam(); self._stop_vid(); self.video.close()
            a = self.video.load(path)
            if a:
                self._vid_info.configure(text=f"{a.path.name} | {a.duration:.1f}s")
                self._vid_slider.configure(to=a.frame_count-1); self._vid_slider.set(0)
                self._vid_loop()
                self.nb.select(1)

    # ════════════════════════════════════════════════════════════
    #  TAB 4: AI COACH (lazy)
    # ════════════════════════════════════════════════════════════

    def _build_ai_coach(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="  🤖 AI Coach  ")
        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = ttk.Frame(pw, style="Card.TFrame")
        pw.add(left, weight=35)

        ttk.Label(left, text="🤖 AI Coach", style="Heading.TLabel").pack(padx=16, pady=(16, 4))
        ttk.Label(left, text="Get AI-powered feedback on your shooting\nor player stats.",
                  foreground=C["subtext"]).pack(padx=16, pady=(0, 12))
        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16)

        ttk.Label(left, text="API Status", style="Heading.TLabel").pack(padx=16, pady=(12, 4))
        self._ai_status_lbl = ttk.Label(left, text="Checking…", foreground=C["orange"])
        self._ai_status_lbl.pack(padx=16, pady=(0, 8))
        tk.Button(left, text="⚙ API Settings…", font=(F, 11), bg=C["card2"], fg=C["text"],
                  relief=tk.FLAT, cursor="hand2", padx=12, pady=4,
                  command=self._open_settings).pack(padx=16, pady=4, fill=tk.X)

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16, pady=(12, 0))
        ttk.Label(left, text="Shot Analysis", style="Heading.TLabel").pack(padx=16, pady=(12, 4))
        tk.Button(left, text="🚀 Analyze Shots with AI", font=(F, 12, "bold"),
                  bg=C["accent2"], fg="#fff", relief=tk.FLAT, cursor="hand2",
                  padx=14, pady=6, command=self._ai_analyze_shots
                  ).pack(padx=16, pady=4, fill=tk.X)

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16, pady=(12, 0))
        ttk.Label(left, text="Stats Analysis", style="Heading.TLabel").pack(padx=16, pady=(12, 4))
        tk.Button(left, text="📊 Analyze Stats with AI", font=(F, 12, "bold"),
                  bg=C["accent2"], fg="#fff", relief=tk.FLAT, cursor="hand2",
                  padx=14, pady=6, command=self._ai_analyze_stats
                  ).pack(padx=16, pady=4, fill=tk.X)

        self._ai_progress = ttk.Progressbar(left, mode="indeterminate")
        self._ai_progress.pack(fill=tk.X, padx=16, pady=(12, 0))

        right = ttk.Frame(pw, style="Card.TFrame")
        pw.add(right, weight=65)
        ttk.Label(right, text="💬 Coach Feedback", style="Heading.TLabel").pack(padx=16, pady=(14, 8))
        self._ai_output = tk.Text(right, wrap=tk.WORD, font=(F, 12),
                                  bg=C["card"], fg=C["text"], relief=tk.FLAT,
                                  border=0, padx=14, pady=12, state=tk.DISABLED)
        self._ai_output.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))
        for tag, fg, ft in [("h1",C["accent"],(F,18,"bold")),("h2",C["text"],(F,14,"bold")),
                             ("b",C["text"],(F,12,"bold")),("n",C["text"],(F,12)),
                             ("err",C["red"],(F,12))]:
            self._ai_output.tag_configure(tag, font=ft, foreground=fg)
        bb = ttk.Frame(right, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=14, pady=(4, 10))
        ttk.Button(bb, text="Copy", command=self._ai_copy).pack(side=tk.LEFT, padx=2)
        ttk.Button(bb, text="Clear", command=self._ai_clear).pack(side=tk.LEFT, padx=2)
        self._refresh_ai_status()

    def _refresh_ai_status(self):
        if not hasattr(self, '_ai_status_lbl'): return
        cfg = _lazy_config()
        if cfg.has_api_key():
            ai = _lazy_ai()
            self._ai_status_lbl.configure(text="🔑 Ready · " + ai.get_model(), foreground=C["green"])
        else:
            self._ai_status_lbl.configure(text="Not configured — click Settings", foreground=C["orange"])

    def _ai_analyze_shots(self):
        if not hasattr(self, '_vid_canvas') or self.video.analysis is None or self.video.analysis.total_shots == 0:
            messagebox.showinfo("No shots", "Go to Video tab, load a video, and mark shots first.")
            return
        try:
            cfg = _lazy_config()
            if not cfg.has_api_key():
                self._open_settings(); return
            ai = _lazy_ai()
            self._ai_run_thread(lambda: ai.analyze_shooting(
                shot_data=self.video.get_consistency_report(),
                player_name="Player",
            ))
        except Exception as e:
            messagebox.showerror("AI Error", str(e))

    def _ai_analyze_stats(self):
        if self._current_result is None:
            messagebox.showinfo("No data", "Run stat analysis first (Analyze tab)."); return
        try:
            cfg = _lazy_config()
            if not cfg.has_api_key():
                self._open_settings(); return
            r = self._current_result
            data = {
                "name": r.player.name,
                "position": r.player.position.value,
                "level": r.player.competition_level.value,
                "stats": {
                    "ppg": r.player.stats.points_per_game,
                    "apg": r.player.stats.assists_per_game,
                    "rpg": r.player.stats.rebounds_per_game,
                    "spg": r.player.stats.steals_per_game,
                    "bpg": r.player.stats.blocks_per_game,
                    "topg": r.player.stats.turnovers_per_game,
                    "fg%": f"{r.player.stats.field_goal_pct:.1%}",
                    "3p%": f"{r.player.stats.three_point_pct:.1%}",
                    "ft%": f"{r.player.stats.free_throw_pct:.1%}",
                },
                "weaknesses": [{"category": w.category, "severity": f"{w.severity:.0%}"}
                               for w in r.weaknesses[:3]],
            }
            ai = _lazy_ai()
            self._ai_run_thread(lambda: ai.analyze_player_stats(data))
        except Exception as e:
            messagebox.showerror("AI Error", str(e))

    def _ai_run_thread(self, fn):
        self._ai_progress.start(8)
        self._ai_output.configure(state=tk.NORMAL)
        self._ai_output.delete("1.0", tk.END)
        self._ai_output.insert("1.0", "Thinking…", "n")
        self._ai_output.configure(state=tk.DISABLED)
        self._status_lbl.configure(text="AI analyzing…")

        def _run():
            result = fn()
            self.after(0, lambda: self._ai_show_result(result))
        threading.Thread(target=_run, daemon=True).start()

    def _ai_show_result(self, result):
        self._ai_progress.stop()
        self._status_lbl.configure(text="Ready")
        self._ai_output.configure(state=tk.NORMAL)
        self._ai_output.delete("1.0", tk.END)
        if "error" in result:
            self._ai_output.insert("1.0", f"Error: {result['error']}\n\nCheck API Settings.", "err")
        else:
            for line in result.get("analysis", "No response").split("\n"):
                if line.startswith("## ") or line.startswith("### "):
                    self._ai_output.insert(tk.END, line.lstrip("# ").strip()+"\n", "h2")
                elif line.startswith("# "):
                    self._ai_output.insert(tk.END, line.lstrip("# ").strip()+"\n", "h1")
                elif line.startswith("**"):
                    self._ai_output.insert(tk.END, line+"\n", "b")
                else:
                    self._ai_output.insert(tk.END, line+"\n", "n")
        self._ai_output.configure(state=tk.DISABLED)

    def _ai_copy(self):
        text = self._ai_output.get("1.0", tk.END).strip()
        if text: self.clipboard_clear(); self.clipboard_append(text)

    def _ai_clear(self):
        self._ai_output.configure(state=tk.NORMAL)
        self._ai_output.delete("1.0", tk.END)
        self._ai_output.configure(state=tk.DISABLED)

    def _open_settings(self):
        SettingsDialog(self, self._refresh_ai_status)

    # ════════════════════════════════════════════════════════════
    #  TAB 5: COMPARE (lazy)
    # ════════════════════════════════════════════════════════════

    def _build_compare(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="  ⚖ Compare  ")
        self._compare_text = tk.Text(tab, wrap=tk.WORD, font=(F, 13),
                                     bg=C["card"], fg=C["text"], relief=tk.FLAT,
                                     border=0, padx=20, pady=20, state=tk.DISABLED)
        self._compare_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        for tag, fg, sz in [("h1",C["text"],18),("h2",C["text"],13),
                             ("g",C["green"],13),("r",C["red"],13),
                             ("o",C["orange"],13),("n",C["text"],13)]:
            self._compare_text.tag_configure(tag, font=(F, sz, "bold" if sz>=18 else "normal"),
                                             foreground=fg)
        bb = ttk.Frame(tab, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=8, pady=(0,8))
        ttk.Button(bb, text="Clear", command=self._clear_compare).pack(side=tk.LEFT, padx=4)

    def _refresh_compare(self):
        if not hasattr(self, '_compare_text'): return
        self._compare_text.configure(state=tk.NORMAL)
        self._compare_text.delete("1.0", tk.END)
        if len(self._compare)==0:
            self._compare_text.insert("1.0", "Add players from Analyze tab.\n", "n")
        elif len(self._compare)==1:
            self._compare_text.insert("1.0", f"{self._compare[0].player.name}\n\nAdd another.", "n")
        else:
            r1,r2=self._compare
            self._compare_text.insert("1.0", f"{r1.player.name}  vs  {r2.player.name}\n", "h1")
            self._compare_text.insert(tk.END, f"{'='*50}\n\n", "n")
            cats=set()
            for w in r1.weaknesses+r2.weaknesses: cats.add(w.category)
            for cat in sorted(cats):
                w1=next((w for w in r1.weaknesses if w.category==cat),None)
                w2=next((w for w in r2.weaknesses if w.category==cat),None)
                t1="g" if w1 is None else ("r" if w1.severity>0.5 else "o" if w1.severity>0.25 else "g")
                t2="g" if w2 is None else ("r" if w2.severity>0.5 else "o" if w2.severity>0.25 else "g")
                s1=f"{w1.severity:.0%}" if w1 else "✓"; s2=f"{w2.severity:.0%}" if w2 else "✓"
                self._compare_text.insert(tk.END, f"{cat:<26} ","n")
                self._compare_text.insert(tk.END, f"{s1:<14}",t1)
                self._compare_text.insert(tk.END, f" {s2}\n",t2)
        self._compare_text.configure(state=tk.DISABLED)

    def _clear_compare(self): self._compare.clear(); self._refresh_compare()

    # ════════════════════════════════════════════════════════════
    #  TAB 6: HISTORY (lazy)
    # ════════════════════════════════════════════════════════════

    def _build_history(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="  📋 History  ")
        self._hist_tree = ttk.Treeview(tab, columns=("player","pos","score","date"),
                                       show="headings", height=14)
        for c, w in [("player",220), ("pos",130), ("score",80), ("date",160)]:
            self._hist_tree.heading(c, text=c.title())
            self._hist_tree.column(c, width=w)
        self._hist_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        bb = ttk.Frame(tab, style="Card.TFrame")
        bb.pack(fill=tk.X, padx=8, pady=(0,8))
        ttk.Button(bb, text="Clear", command=self._clear_history).pack(side=tk.LEFT, padx=4)
    def _save_history(self, r):
        from datetime import datetime
        self._hist_tree.insert("", 0, values=(r.player.name, r.player.position.value,
                                               f"{r.overall_score:.0%}",
                                               datetime.now().strftime("%Y-%m-%d %H:%M")))

    def _clear_history(self):
        if hasattr(self, '_hist_tree'):
            for i in self._hist_tree.get_children(): self._hist_tree.delete(i)

    # ── Cleanup ────────────────────────────────────────────────

    def destroy(self):
        self._stop_cam(); self._stop_vid()
        if self._camera: self._camera.close()
        if self._video: self._video.close()
        super().destroy()


# ════════════════════════════════════════════════════════════════
#  SETTINGS DIALOG
# ════════════════════════════════════════════════════════════════

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, on_close=None):
        super().__init__(parent)
        self.title("API Settings")
        self.geometry("500x380")
        self.resizable(False, False)
        self.configure(bg=C["card"])
        self.transient(parent); self.grab_set()
        self._on_close = on_close

        ttk.Label(self, text="⚙ API Settings", style="Heading.TLabel").pack(padx=20, pady=(16,4))
        ttk.Label(self, text="MiniMax Token Plan API key and model.",
                  foreground=C["subtext"]).pack(padx=20, pady=(0,12))
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20)

        # Key
        ttk.Label(self, text="API Key", style="Heading.TLabel").pack(padx=20, pady=(12,4), anchor="w")
        kf = ttk.Frame(self, style="Card.TFrame")
        kf.pack(fill=tk.X, padx=20)
        self._key_entry = ttk.Entry(kf, width=48, show="•")
        self._key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(kf, text="Show", command=lambda: self._key_entry.configure(
            show="" if self._key_entry.cget("show")=="•" else "•")).pack(side=tk.RIGHT, padx=(4,0))
        cfg = _lazy_config()
        existing = cfg.load_api_key()
        if existing: self._key_entry.insert(0, existing)
        ttk.Label(self, text="Encrypted before storage, never leaves your computer.",
                  foreground=C["subtext"], font=(F,9)).pack(padx=20, pady=(2,0), anchor="w")

        # Model
        ttk.Label(self, text="Model", style="Heading.TLabel").pack(padx=20, pady=(12,4), anchor="w")
        mf = ttk.Frame(self, style="Card.TFrame")
        mf.pack(fill=tk.X, padx=20)
        ai = _lazy_ai()
        self._model_var = tk.StringVar(value=ai.get_model())
        cb = ttk.Combobox(mf, textvariable=self._model_var, values=ai.get_available_models(), width=44)
        cb.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Buttons
        bf = ttk.Frame(self, style="Card.TFrame")
        bf.pack(fill=tk.X, padx=20, pady=(12,8))
        ttk.Button(bf, text="🔍 Test", command=self._test).pack(side=tk.LEFT, padx=2)
        ttk.Button(bf, text="💾 Save", command=self._save).pack(side=tk.RIGHT, padx=2)
        ttk.Button(bf, text="🗑 Clear", command=self._clear).pack(side=tk.RIGHT, padx=2)

        self._test_lbl = ttk.Label(self, text="", font=(F,10), foreground=C["subtext"], wraplength=440)
        self._test_lbl.pack(padx=20, pady=(4,0))
        ttk.Label(self, text="Token Plan keys from platform.minimaxi.com",
                  foreground=C["subtext"], font=(F,9,"italic")).pack(padx=20, pady=(4,10))

    def _test(self):
        key = self._key_entry.get().strip()
        model = self._model_var.get().strip()
        if not key:
            self._test_lbl.configure(text="Enter API key first.", foreground=C["red"]); return
        cfg = _lazy_config(); ai = _lazy_ai()
        old_key = cfg.load_api_key(); old_model = ai.get_model()
        cfg.clear_api_key(); cfg.save_api_key(key)
        if model: ai.save_model(model)
        self._test_lbl.configure(text="Testing…", foreground=C["subtext"]); self.update()
        result = ai.test_connection()
        if result.get("ok"):
            self._test_lbl.configure(text=f"✅ Connected! Model: {result.get('model')}", foreground=C["green"])
        else:
            self._test_lbl.configure(text=f"❌ {result.get('error','Failed')}", foreground=C["red"])
            cfg.clear_api_key()
            if old_key: cfg.save_api_key(old_key)
            if old_model: ai.save_model(old_model)

    def _save(self):
        key = self._key_entry.get().strip(); model = self._model_var.get().strip()
        cfg = _lazy_config(); ai = _lazy_ai()
        if key: cfg.save_api_key(key)
        if model: ai.save_model(model)
        if self._on_close: self._on_close()
        self._test_lbl.configure(text="✅ Saved!", foreground=C["green"])
        self.after(800, self.destroy)

    def _clear(self):
        _lazy_config().clear_api_key()
        self._key_entry.delete(0, tk.END)
        self._test_lbl.configure(text="Key cleared.", foreground=C["orange"])


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
