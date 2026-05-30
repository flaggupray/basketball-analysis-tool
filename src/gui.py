"""Basketball Inability Analyzer — lightweight, responsive GUI."""

from __future__ import annotations

import json, threading, time, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from src.models import Player, GameStats, Position, CompetitionLevel
from src.analyzer import WeaknessAnalyzer

F = "Helvetica Neue"

# ── Lazy module loaders ────────────────────────────────────────

def _lazy_camera(): from src.camera import CameraManager; return CameraManager
def _lazy_video():   from src.video_analyzer import VideoAnalyzer; return VideoAnalyzer
def _lazy_config():  import src.config as m; return m
def _lazy_ai():      from src.ai_analyzer import analyze_shooting, analyze_player_stats, test_connection; return analyze_shooting, analyze_player_stats, test_connection
def _lazy_np():      import numpy as np; return np
def _lazy_pil():     from PIL import Image, ImageTk; return Image, ImageTk


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Basketball Analyzer")
        self.geometry("1050x720")
        self.minsize(800, 560)
        self.configure(bg="#1a1a2e")

        self.analyzer = WeaknessAnalyzer()
        self._cam = self._vid = None
        self._cam_job = self._vid_job = None
        self._current_result = None
        self._compare: list = []
        self._click_pos = None

        self._built: set[str] = set()
        self._build()

    @property
    def cam(self):
        if self._cam is None: self._cam = _lazy_camera()()
        return self._cam
    @property
    def vid(self):
        if self._vid is None: self._vid = _lazy_video()()
        return self._vid

    def _build(self):
        tk.Label(self, text="🏀  Basketball Analyzer", font=(F, 18, "bold"),
                 fg="#eef0f6", bg="#1a1a2e").pack(pady=(14, 2))
        self._status = tk.Label(self, text="Ready", font=(F, 10),
                                fg="#8b8daa", bg="#1a1a2e")
        self._status.pack()

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 10))
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab)

        # Add ALL tab placeholders at startup (so user sees every tab)
        # Only Analyze gets real content; others are empty until clicked
        self._tab_frames: dict[str, ttk.Frame] = {}
        for key, title in [("A","  📊 Analyze  "), ("V","  🎬 Video  "),
                           ("C","  📷 Camera  "), ("I","  🤖 AI Coach  "),
                           ("M","  ⚖ Compare  "), ("H","  📋 History  ")]:
            f = ttk.Frame(self.nb)
            self._tab_frames[key] = f
            self.nb.add(f, text=title)
            if key != "A":
                ttk.Label(f, text=f"Click to load {title.strip()}",
                          font=(F, 12), foreground="#888").pack(expand=True)

        self._build_analyze_content()

    def _on_tab(self, e):
        name = self.nb.tab(self.nb.index("current"), "text")
        if "Video" in name and "V" not in self._built:
            self._build_video_content()
        elif "Camera" in name and "C" not in self._built:
            self._build_camera_content()
        elif "AI Coach" in name and "I" not in self._built:
            self._build_ai_content()
        elif "Compare" in name and "M" not in self._built:
            self._build_compare_content()
        elif "History" in name and "H" not in self._built:
            self._build_history_content()

    # ═══ ANALYZE (built at startup) ═══════════════════════════

    def _build_analyze_content(self):
        self._built.add("A")
        tab = self._tab_frames["A"]
        for w in tab.winfo_children(): w.destroy()
        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._build_form(pw)
        self._build_result(pw)

    def _build_form(self, pw):
        f = ttk.Frame(pw, padding=8)
        pw.add(f, weight=38)
        self.fields = {}
        rows = [
            ("Name:", "name", "e", ""),
            ("Position:", "pos", "c", "Shooting Guard"),
            ("Level:", "lvl", "c", "high_school"),
            ("Games:", "gp", "e", "20"),
            ("Min/Game:", "mpg", "e", "28"),
            ("PPG:", "ppg", "e", "0.0"),
            ("APG:", "apg", "e", "0.0"),
            ("RPG:", "rpg", "e", "0.0"),
            ("SPG:", "spg", "e", "0.0"),
            ("BPG:", "bpg", "e", "0.0"),
            ("TO:", "to", "e", "0.0"),
            ("FG%:", "fg", "e", "0.00"),
            ("3P%:", "tp", "e", "0.00"),
            ("FT%:", "ft", "e", "0.00"),
        ]
        for i, (lbl, key, typ, default) in enumerate(rows):
            ttk.Label(f, text=lbl, font=(F, 10)).grid(row=i, column=0, sticky="e", padx=(4, 6), pady=1)
            if typ == "c":
                vals = [p.value for p in Position] if key == "pos" else [l.value for l in CompetitionLevel]
                w = ttk.Combobox(f, values=vals, state="readonly", width=18)
                w.set(default)
            else:
                w = ttk.Entry(f, width=20)
                if default: w.insert(0, default)
            w.grid(row=i, column=1, sticky="w", pady=1)
            self.fields[key] = w
        ttk.Button(f, text="🔍 Analyze", command=self._do_analyze).grid(
            row=len(rows), column=0, columnspan=2, pady=(10, 0))
        ttk.Button(f, text="Load JSON…", command=self._load_json).grid(
            row=len(rows)+1, column=0, columnspan=2)
        ttk.Button(f, text="Clear", command=self._clear_form).grid(
            row=len(rows)+2, column=0, columnspan=2)

    def _build_result(self, pw):
        f = ttk.Frame(pw, padding=8)
        pw.add(f, weight=62)
        self._r_title = ttk.Label(f, text="Your Analysis", font=(F, 14, "bold"))
        self._r_title.pack(anchor="w")
        self._r_score = tk.Label(f, text="—", font=(F, 30, "bold"), fg="#ff5e5b", bg="#f0f0f0")
        self._r_score.pack(anchor="e", pady=(0, 4))
        self._r_summary = ttk.Label(f, text="Fill in your stats and click Analyze.", wraplength=400)
        self._r_summary.pack(anchor="w", pady=(0, 6))

        self._r_tree = ttk.Treeview(f, columns=("cat","sev"), show="headings", height=10)
        self._r_tree.heading("cat", text="Weakness"); self._r_tree.heading("sev", text="Severity")
        self._r_tree.column("cat", width=280); self._r_tree.column("sev", width=80, anchor="center")
        self._r_tree.pack(fill=tk.BOTH, expand=True, pady=4)

        self._r_rec = tk.Text(f, height=3, wrap=tk.WORD, font=(F, 10), relief=tk.FLAT, border=0, padx=4, pady=4)
        self._r_rec.pack(fill=tk.X, pady=2)

        bb = ttk.Frame(f)
        bb.pack(fill=tk.X, pady=4)
        ttk.Button(bb, text="Export Report", command=self._export).pack(side=tk.LEFT, padx=2)
        ttk.Button(bb, text="Add to Compare", command=self._add_cmp).pack(side=tk.LEFT, padx=2)

    def _read_form(self):
        try:
            name = self.fields["name"].get().strip() or "Player"
            pm = {p.value: p for p in Position}
            pos = pm[self.fields["pos"].get()]
            lm = {l.value: l for l in CompetitionLevel}
            lvl = lm[self.fields["lvl"].get()]
            s = GameStats(
                points_per_game=float(self.fields["ppg"].get()),
                assists_per_game=float(self.fields["apg"].get()),
                rebounds_per_game=float(self.fields["rpg"].get()),
                steals_per_game=float(self.fields["spg"].get()),
                blocks_per_game=float(self.fields["bpg"].get()),
                turnovers_per_game=float(self.fields["to"].get()),
                field_goal_pct=float(self.fields["fg"].get()),
                three_point_pct=float(self.fields["tp"].get()),
                free_throw_pct=float(self.fields["ft"].get()),
                games_played=int(self.fields["gp"].get()),
                minutes_per_game=float(self.fields["mpg"].get()),
            )
            return Player(name=name, position=pos, stats=s, competition_level=lvl)
        except Exception as e:
            messagebox.showerror("Check Input", str(e))
            return None

    def _do_analyze(self):
        p = self._read_form()
        if p is None: return
        self._current_result = self.analyzer.analyze(p)
        r = self._current_result
        for i in self._r_tree.get_children(): self._r_tree.delete(i)
        sc = r.overall_score
        self._r_score.configure(text=f"{sc:.0%}", fg="#00d2a0" if sc>=0.8 else "#ffa502" if sc>=0.6 else "#ff4757")
        self._r_title.configure(text=f"{r.player.name} — {r.player.position.value}")
        lines = r.summary.split("\n")
        self._r_summary.configure(text=lines[3] if len(lines)>3 else "")
        for i, w in enumerate(r.weaknesses, 1):
            tag = f"s{i}"
            self._r_tree.insert("", tk.END, values=(f"{i}. {w.category}", f"{w.severity:.0%}"), tags=(tag,))
            if w.severity>0.5: self._r_tree.tag_configure(tag, foreground="#ff4757")
            elif w.severity>0.25: self._r_tree.tag_configure(tag, foreground="#ffa502")
        self._r_rec.delete("1.0", tk.END)
        if r.weaknesses:
            self._r_rec.insert("1.0", f"🎯 {r.weaknesses[0].category}: {r.weaknesses[0].recommendation}")
        self._save_hist(r)

    def _load_json(self):
        p = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not p: return
        with open(p) as f: data = json.load(f)
        if isinstance(data, list): data = data[0]
        pm = {pp.value: pp.name for pp in Position}
        self.fields["pos"].set(pm.get(data.get("position","SG"), "Shooting Guard"))
        self.fields["lvl"].set(data.get("competition_level","high_school"))
        for k, fk in [("name","name"),("games_played","gp"),("minutes_per_game","mpg"),
                       ("points_per_game","ppg"),("assists_per_game","apg"),
                       ("rebounds_per_game","rpg"),("steals_per_game","spg"),
                       ("blocks_per_game","bpg"),("turnovers_per_game","to"),
                       ("field_goal_pct","fg"),("three_point_pct","tp"),
                       ("free_throw_pct","ft")]:
            if k in data: self.fields[fk].delete(0,tk.END); self.fields[fk].insert(0,str(data[k]))

    def _clear_form(self):
        defaults = {"name":"","gp":"20","mpg":"28","ppg":"0.0","apg":"0.0","rpg":"0.0",
                    "spg":"0.0","bpg":"0.0","to":"0.0","fg":"0.00","tp":"0.00","ft":"0.00"}
        for k, w in self.fields.items():
            if isinstance(w, ttk.Entry): w.delete(0,tk.END); w.insert(0,defaults.get(k,"0.0"))

    def _export(self):
        if self._current_result is None: return
        p = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown","*.md"),("JSON","*.json")])
        if not p: return
        r = self._current_result
        if p.endswith(".json"):
            json.dump({"player":r.player.name,"position":r.player.position.value,
                       "overall_score":r.overall_score,
                       "weaknesses":[{"category":w.category,"severity":w.severity,
                                      "recommendation":w.recommendation} for w in r.weaknesses],
                       "strengths":r.strengths}, open(p,"w"), indent=2)
        else:
            lines = [f"# {r.player.name} — Weakness Report","",
                     f"**Score:** {r.overall_score:.0%}","",
                     "| # | Category | Severity | Recommendation |",
                     "|---|----------|----------|----------------|"]
            for i,w in enumerate(r.weaknesses,1):
                lines.append(f"| {i} | {w.category} | {w.severity:.0%} | {w.recommendation} |")
            open(p,"w").write("\n".join(lines))
        messagebox.showinfo("Done", f"Saved:\n{p}")

    def _add_cmp(self):
        if self._current_result is None: return
        if len(self._compare) < 2: self._compare.append(self._current_result)
        if "M" not in self._built: self._build_compare_content()
        self._refresh_cmp()

    # ═══ VIDEO (lazy) ══════════════════════════════════════════

    def _build_video_content(self):
        self._built.add("V")
        tab = self._tab_frames["V"]
        for w in tab.winfo_children(): w.destroy()
        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        vf = ttk.Frame(pw, padding=4)
        pw.add(vf, weight=68)
        self._v_canvas = tk.Canvas(vf, bg="#000", height=300)
        self._v_canvas.pack(fill=tk.BOTH, expand=True)
        self._v_canvas.bind("<Button-1>", self._v_click)
        self._v_slider = ttk.Scale(vf, from_=0, to=100, command=self._v_seek_slider)
        self._v_slider.pack(fill=tk.X, pady=2)

        ctrl = ttk.Frame(vf)
        ctrl.pack(fill=tk.X)
        for t, c in [("<", lambda: self._v_step(-1)), ("▶", self._v_pause),
                     (">", lambda: self._v_step(1)), ("+10", lambda: self._v_step(10))]:
            ttk.Button(ctrl, text=t, command=c, width=4).pack(side=tk.LEFT, padx=1)
        self._v_info = ttk.Label(vf, text="Click 'Load Video…'",
                                 font=(F, 9), foreground="#888")
        self._v_info.pack(fill=tk.X, pady=2)
        ttk.Button(vf, text="Load Video…", command=self._v_load).pack(pady=2)

        sf = ttk.Frame(pw, padding=4)
        pw.add(sf, weight=32)
        ttk.Label(sf, text="Shot Tracking", font=(F, 12, "bold")).pack(pady=4)
        self._v_counter = tk.Label(sf, text="0M / 0X", font=(F, 14, "bold"))
        self._v_counter.pack()
        for t, c in [("✅ Make", lambda: self._v_mark("make")),
                     ("❌ Miss", lambda: self._v_mark("miss")),
                     ("📍 Arc", self._v_arc), ("↩ Undo", self._v_undo)]:
            ttk.Button(sf, text=t, command=c).pack(fill=tk.X, padx=8, pady=1)
        ttk.Button(sf, text="Export Analysis", command=self._v_export).pack(fill=tk.X, padx=8, pady=(8, 0))

    def _v_load(self):
        p = filedialog.askopenfilename(filetypes=[("Video","*.mp4 *.mov *.avi *.mkv")])
        if not p: return
        self._v_stop(); a = self.vid.load(p)
        if a is None: messagebox.showerror("Error", f"Cannot open:\n{p}"); return
        self._v_info.configure(text=f"{a.path.name}  {a.duration:.0f}s  {a.resolution[0]}x{a.resolution[1]}")
        self._v_slider.configure(to=a.frame_count-1); self._v_slider.set(0)
        self._v_counter.configure(text="0M / 0X"); self._v_start()

    def _v_start(self):
        self._v_stop()
        def _l():
            try:
                if self.vid.analysis is None: return
                if not self.vid.paused:
                    self.vid.get_frame()
                    self.vid._current_frame_idx += 1
                    if self.vid._current_frame_idx >= self.vid.analysis.frame_count:
                        self.vid._current_frame_idx = 0
                    self._v_slider.set(self.vid._current_frame_idx)
                self._v_render()
            except Exception: pass
            self._vid_job = self.after(50, _l)
        _l()

    def _v_stop(self):
        if self._vid_job: self.after_cancel(self._vid_job); self._vid_job = None

    def _v_render(self):
        frame = self.vid.get_annotated_frame()
        if frame is None: return
        cw = self._v_canvas.winfo_width(); ch = self._v_canvas.winfo_height()
        if cw<10 or ch<10: return
        h,w = frame.shape[:2]; scale = min(cw/w, ch/h)
        nw, nh = int(w*scale), int(h*scale)
        Image, ImageTk = _lazy_pil()
        img = Image.fromarray(frame).resize((nw,nh), Image.LANCZOS)
        self._v_img = ImageTk.PhotoImage(img)
        self._v_canvas.delete("all")
        self._v_canvas.create_image(cw//2, ch//2, image=self._v_img)

    def _v_seek_slider(self, val):
        if self.vid.analysis: self.vid.seek(int(float(val)))
    def _v_step(self, d):
        self.vid.seek_relative(d)
        if self.vid.analysis: self._v_slider.set(self.vid.current_frame_idx)
        self._v_render()
    def _v_pause(self): self.vid.toggle_pause()
    def _v_click(self, evt):
        if self.vid.analysis is None: return
        cw=self._v_canvas.winfo_width(); ch=self._v_canvas.winfo_height()
        h,w=self.vid.analysis.resolution
        scale=min(cw/w,ch/h); ox=(cw-w*scale)/2; oy=(ch-h*scale)/2
        if w*scale>0 and h*scale>0:
            self._click_pos=(max(0,min((evt.x-ox)/(w*scale),1)), max(0,min((evt.y-oy)/(h*scale),1)))
    def _v_mark(self, r):
        self.vid.mark_shot(r, getattr(self,"_click_pos",None))
        a=self.vid.analysis
        if a: self._v_counter.configure(text=f"{a.makes}M / {a.misses}X")
    def _v_arc(self):
        bp=getattr(self,"_click_pos",None)
        if bp: self.vid.mark_arc_point(bp)
        a=self.vid.analysis
        if a and a.shots: self.vid.estimate_release_angle(len(a.shots)-1)
    def _v_undo(self):
        self.vid.undo_last_shot()
        a=self.vid.analysis
        if a: self._v_counter.configure(text=f"{a.makes}M / {a.misses}X")
    def _v_export(self):
        if self.vid.analysis is None: return
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if p: self.vid.export_analysis(p); messagebox.showinfo("Done", f"Saved:\n{p}")

    # ═══ CAMERA (lazy) ═════════════════════════════════════════

    def _build_camera_content(self):
        self._built.add("C")
        tab = self._tab_frames["C"]
        for w in tab.winfo_children(): w.destroy()
        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        vf = ttk.Frame(pw, padding=4)
        pw.add(vf, weight=65)
        self._c_canvas = tk.Canvas(vf, bg="#000", height=300)
        self._c_canvas.pack(fill=tk.BOTH, expand=True)
        ctrl = ttk.Frame(vf)
        ctrl.pack(fill=tk.X, pady=4)
        self._c_status = ttk.Label(ctrl, text="Off", foreground="#888")
        self._c_status.pack(side=tk.LEFT)
        self._c_rec_btn = ttk.Button(ctrl, text="🔴 Record", command=self._c_toggle)
        self._c_rec_btn.pack(side=tk.RIGHT, padx=2)
        ttk.Button(ctrl, text="📷 Open", command=self._c_open).pack(side=tk.RIGHT, padx=2)
        self._c_timer = tk.Label(vf, text="", font=(F, 12, "bold"), fg="red")
        self._c_timer.pack()

        sf = ttk.Frame(pw, padding=4)
        pw.add(sf, weight=35)
        ttk.Label(sf, text="Recordings", font=(F, 12, "bold")).pack(pady=4)
        self._c_list = tk.Listbox(sf, height=12)
        self._c_list.pack(fill=tk.BOTH, expand=True, pady=4)
        self._c_list.bind("<Double-1>", lambda e: self._c_play())
        ttk.Button(sf, text="▶ Play Selected", command=self._c_play).pack(fill=tk.X, padx=4, pady=2)
        ttk.Button(sf, text="Clear List", command=lambda: self._c_list.delete(0,tk.END)).pack(fill=tk.X, padx=4)

    def _c_open(self):
        try:
            if self.cam.is_open: self._c_close()
            if self.cam.open(0):
                self._c_status.configure(text="Live", foreground="green"); self._c_start()
            else:
                self._c_status.configure(text="No camera", foreground="red")
        except Exception as e:
            self._c_status.configure(text="Error", foreground="red")
            messagebox.showerror("Camera Error", str(e))

    def _c_close(self):
        self._c_stop(); self.cam.close()
        self._c_status.configure(text="Off", foreground="#888")
        self._c_canvas.delete("all")

    def _c_start(self):
        self._c_stop()
        def _l():
            try:
                if not self.cam.is_open: return
                frame = self.cam.preview_frame()
                if frame is not None:
                    cw=self._c_canvas.winfo_width(); ch=self._c_canvas.winfo_height()
                    if cw>10 and ch>10:
                        h,w=frame.shape[:2]; scale=min(cw/w,ch/h)
                        Image, ImageTk = _lazy_pil()
                        img=Image.fromarray(frame).resize((int(w*scale),int(h*scale)),Image.LANCZOS)
                        self._c_img=ImageTk.PhotoImage(img)
                        self._c_canvas.delete("all")
                        self._c_canvas.create_image(cw//2,ch//2,image=self._c_img)
                if self.cam.is_recording:
                    self.cam.write_frame(frame)
                    self._c_timer.configure(text=f"🔴 {time.time()-self.cam._start_time:.0f}s")
            except Exception: pass
            self._cam_job=self.after(66, _l)
        _l()

    def _c_stop(self):
        if self._cam_job: self.after_cancel(self._cam_job); self._cam_job=None

    def _c_toggle(self):
        if not self.cam.is_open: return
        if self.cam.is_recording:
            rec=self.cam.stop_recording(); self._c_rec_btn.configure(text="🔴 Record")
            self._c_timer.configure(text="")
            if rec: self._c_list.insert(0, f"{rec.path.name} ({rec.duration:.1f}s)")
        else:
            if self.cam.start_recording(str(Path.home()/"Desktop")):
                self._c_rec_btn.configure(text="⏹ Stop")

    def _c_play(self):
        sel=self._c_list.curselection()
        if not sel: return
        name=self._c_list.get(sel[0]).split(" (")[0]
        path=str(Path.home()/"Desktop"/name)
        if Path(path).exists():
            self._c_stop(); self._v_stop(); self.vid.close()
            a=self.vid.load(path)
            if a:
                if "V" not in self._built: self._build_video_content()
                self._v_info.configure(text=f"{a.path.name}  {a.duration:.0f}s")
                self._v_slider.configure(to=a.frame_count-1); self._v_slider.set(0)
                self._v_start(); self.nb.select(len([t for t in self.nb.tabs()])-4)

    # ═══ AI COACH (lazy) ═══════════════════════════════════════

    def _build_ai_content(self):
        self._built.add("I")
        tab = self._tab_frames["I"]
        for w in tab.winfo_children(): w.destroy()
        pw = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        lf = ttk.Frame(pw, padding=8)
        pw.add(lf, weight=32)
        ttk.Label(lf, text="AI Coach", font=(F, 14, "bold")).pack(pady=4)
        self._ai_status_lbl = ttk.Label(lf, text="Checking…", foreground="#888")
        self._ai_status_lbl.pack()
        ttk.Button(lf, text="⚙ API Settings…", command=self._ai_settings).pack(fill=tk.X, pady=4)
        ttk.Button(lf, text="🚀 Analyze Shots with AI", command=self._ai_shots).pack(fill=tk.X, pady=2)
        ttk.Button(lf, text="📊 Analyze Stats with AI", command=self._ai_stats).pack(fill=tk.X, pady=2)
        self._ai_bar = ttk.Progressbar(lf, mode="indeterminate")
        self._ai_bar.pack(fill=tk.X, pady=8)

        rf = ttk.Frame(pw, padding=8)
        pw.add(rf, weight=68)
        ttk.Label(rf, text="Coach Feedback", font=(F, 14, "bold")).pack(anchor="w")
        self._ai_out = tk.Text(rf, wrap=tk.WORD, font=(F, 11), relief=tk.FLAT,
                               border=0, padx=8, pady=8, state=tk.DISABLED)
        self._ai_out.pack(fill=tk.BOTH, expand=True, pady=4)
        bb = ttk.Frame(rf)
        bb.pack(fill=tk.X)
        ttk.Button(bb, text="Copy", command=lambda: self.clipboard_append(
            self._ai_out.get("1.0",tk.END).strip())).pack(side=tk.LEFT, padx=2)
        ttk.Button(bb, text="Clear", command=lambda: [self._ai_out.configure(state=tk.NORMAL),
                   self._ai_out.delete("1.0",tk.END), self._ai_out.configure(state=tk.DISABLED)]
                   ).pack(side=tk.LEFT, padx=2)
        self._ai_refresh_status()

    def _ai_refresh_status(self):
        try:
            c = _lazy_config().load()
            if c.get("key"):
                self._ai_status_lbl.configure(
                    text=f"🔑 Ready · {c.get('model','?')}", foreground="green")
            else:
                self._ai_status_lbl.configure(text="Not configured — click Settings", foreground="orange")
        except Exception:
            self._ai_status_lbl.configure(text="Unknown", foreground="red")

    def _ai_shots(self):
        if "V" not in self._built or self.vid.analysis is None or self.vid.analysis.total_shots==0:
            messagebox.showinfo("No shots", "Load a video and mark shots first."); return
        try:
            cfg=_lazy_config()
            if not cfg.has_key(): self._ai_settings(); return
            analyze_shooting, _, _ = _lazy_ai()
            self._ai_run(lambda: analyze_shooting(shot_data=self.vid.get_consistency_report(), player_name="Player"))
        except Exception as e: messagebox.showerror("AI Error", str(e))

    def _ai_stats(self):
        if self._current_result is None: messagebox.showinfo("No data", "Run analysis first."); return
        try:
            cfg=_lazy_config()
            if not cfg.has_key(): self._ai_settings(); return
            r=self._current_result; _, analyze_player_stats, _ = _lazy_ai()
            self._ai_run(lambda: analyze_player_stats({
                "name":r.player.name,"position":r.player.position.value,
                "level":r.player.competition_level.value,
                "stats":{"ppg":r.player.stats.points_per_game,"apg":r.player.stats.assists_per_game,
                         "rpg":r.player.stats.rebounds_per_game,"fg%":f"{r.player.stats.field_goal_pct:.1%}",
                         "3p%":f"{r.player.stats.three_point_pct:.1%}","ft%":f"{r.player.stats.free_throw_pct:.1%}"},
                "weaknesses":[{"category":w.category,"severity":f"{w.severity:.0%}"} for w in r.weaknesses[:3]],
            }))
        except Exception as e: messagebox.showerror("AI Error", str(e))

    def _ai_run(self, fn):
        self._ai_bar.start(8)
        self._ai_out.configure(state=tk.NORMAL); self._ai_out.delete("1.0",tk.END)
        self._ai_out.insert("1.0","Thinking…"); self._ai_out.configure(state=tk.DISABLED)
        def _r():
            try:
                result=fn()
                self.after(0, lambda: [self._ai_bar.stop(), self._ai_out.configure(state=tk.NORMAL),
                                       self._ai_out.delete("1.0",tk.END),
                                       self._ai_out.insert("1.0", result.get("analysis","No response")
                                           if "error" not in result else f"Error: {result['error']}"),
                                       self._ai_out.configure(state=tk.DISABLED)])
            except Exception as e:
                self.after(0, lambda: [self._ai_bar.stop(), self._ai_out.configure(state=tk.NORMAL),
                                       self._ai_out.delete("1.0",tk.END),
                                       self._ai_out.insert("1.0",f"Error: {e}"),
                                       self._ai_out.configure(state=tk.DISABLED)])
        threading.Thread(target=_r, daemon=True).start()

    def _ai_settings(self):
        cfg = _lazy_config()
        d = tk.Toplevel(self); d.title("AI Provider Settings"); d.geometry("520x520")
        d.resizable(False, False); d.transient(self); d.grab_set()

        c = cfg.load()
        saved_key = c.get("key", "")
        saved_url = c.get("base_url", "")
        saved_model = c.get("model", "")

        ttk.Label(d, text="AI Provider Settings", font=(F, 14, "bold")).pack(padx=16, pady=(12, 4), anchor="w")
        ttk.Label(d, text="Works with OpenAI, MiniMax, Groq, DeepSeek, Ollama, and any OpenAI-compatible API.",
                  font=(F, 9), foreground="#888").pack(padx=16, anchor="w")

        # Provider preset
        ttk.Label(d, text="Provider Preset", font=(F, 11, "bold")).pack(padx=16, pady=(12, 2), anchor="w")
        pv = tk.StringVar(value="Custom")
        providers = list(cfg.PROVIDERS.keys())
        # Detect current provider
        for name, url in cfg.PROVIDERS.items():
            if url and url in saved_url:
                pv.set(name); break
        pc = ttk.Combobox(d, textvariable=pv, values=providers, state="readonly", width=48)
        pc.pack(padx=16, fill=tk.X)

        # Base URL
        ttk.Label(d, text="API Base URL", font=(F, 11, "bold")).pack(padx=16, pady=(8, 2), anchor="w")
        uv = tk.StringVar(value=saved_url or cfg.PROVIDERS["MiniMax"])
        ue = ttk.Entry(d, textvariable=uv, width=52); ue.pack(padx=16, fill=tk.X)

        def _on_provider(*_):
            name = pv.get()
            if name in cfg.PROVIDERS and cfg.PROVIDERS[name]:
                uv.set(cfg.PROVIDERS[name])
            if name in cfg.MODEL_DEFAULTS:
                mv.set(cfg.MODEL_DEFAULTS[name])
        pv.trace("w", _on_provider)

        # API Key
        ttk.Label(d, text="API Key", font=(F, 11, "bold")).pack(padx=16, pady=(8, 2), anchor="w")
        ke = ttk.Entry(d, width=52, show="•"); ke.pack(padx=16, fill=tk.X)
        if saved_key: ke.insert(0, saved_key)
        ttk.Label(d, text="Key is encrypted before storage, never leaves your computer.",
                  font=(F, 8), foreground="#888").pack(padx=16, anchor="w")

        # Model
        ttk.Label(d, text="Model Name", font=(F, 11, "bold")).pack(padx=16, pady=(8, 2), anchor="w")
        mv = tk.StringVar(value=saved_model or cfg.MODEL_DEFAULTS.get(pv.get(), ""))
        ttk.Entry(d, textvariable=mv, width=52).pack(padx=16, fill=tk.X)
        ttk.Label(d, text="Any model your provider supports, e.g. gpt-4o-mini, deepseek-chat, llama3.2",
                  font=(F, 8), foreground="#888").pack(padx=16, anchor="w")

        # Status
        rl = ttk.Label(d, text="", font=(F, 9)); rl.pack(padx=16, pady=(8, 2))

        # Buttons
        bf = ttk.Frame(d); bf.pack(pady=8)
        def _test():
            k = ke.get().strip(); u = uv.get().strip(); m = mv.get().strip()
            if not k: rl.configure(text="Enter API key first.", foreground="red"); return
            cfg.save(key=k, base_url=u, model=m)
            rl.configure(text="Testing…", foreground="#888"); d.update()
            _, _, test_connection = _lazy_ai()
            res = test_connection(key=k, base_url=u, model=m)
            if res.get("ok"): rl.configure(text=f"✅ Connected! Model: {res.get('model','')}", foreground="green")
            else: rl.configure(text=f"❌ {res.get('error','')}", foreground="red")
        ttk.Button(bf, text="🔍 Test Connection", command=_test).pack(side=tk.LEFT, padx=3)

        def _save():
            cfg.save(key=ke.get().strip(), base_url=uv.get().strip(), model=mv.get().strip())
            self._ai_refresh_status(); d.destroy()
        ttk.Button(bf, text="💾 Save", command=_save).pack(side=tk.LEFT, padx=3)

        ttk.Button(bf, text="🗑 Clear All", command=lambda: [
                   cfg.clear(), ke.delete(0, tk.END), uv.set(""), mv.set(""),
                   rl.configure(text="Cleared.", foreground="orange")]
                   ).pack(side=tk.LEFT, padx=3)

    # ═══ COMPARE (lazy) ════════════════════════════════════════

    def _build_compare_content(self):
        self._built.add("M")
        tab = self._tab_frames["M"]
        for w in tab.winfo_children(): w.destroy()
        self._cmp_text = tk.Text(tab, wrap=tk.WORD, font=(F, 12), relief=tk.FLAT,
                                 border=0, padx=16, pady=16, state=tk.DISABLED)
        self._cmp_text.pack(fill=tk.BOTH, expand=True)
        ttk.Button(tab, text="Clear", command=self._clear_cmp).pack(pady=(0,6))
        self._refresh_cmp()

    def _refresh_cmp(self):
        if "M" not in self._built: return
        self._cmp_text.configure(state=tk.NORMAL); self._cmp_text.delete("1.0",tk.END)
        if not self._compare:
            self._cmp_text.insert("1.0","Add players from Analyze tab.\n")
        elif len(self._compare)==1:
            self._cmp_text.insert("1.0",f"{self._compare[0].player.name}\nAdd another.\n")
        else:
            r1,r2=self._compare
            self._cmp_text.insert("1.0",f"{r1.player.name}  vs  {r2.player.name}\n{'='*40}\n\n")
            cats=set()
            for w in r1.weaknesses+r2.weaknesses: cats.add(w.category)
            for cat in sorted(cats):
                w1=next((w for w in r1.weaknesses if w.category==cat),None)
                w2=next((w for w in r2.weaknesses if w.category==cat),None)
                s1=f"{w1.severity:.0%}" if w1 else "✓"
                s2=f"{w2.severity:.0%}" if w2 else "✓"
                self._cmp_text.insert(tk.END, f"{cat:<26} {s1:<10} {s2}\n")
        self._cmp_text.configure(state=tk.DISABLED)

    def _clear_cmp(self): self._compare.clear(); self._refresh_cmp()

    # ═══ HISTORY (lazy) ════════════════════════════════════════

    def _build_history_content(self):
        self._built.add("H")
        tab = self._tab_frames["H"]
        for w in tab.winfo_children(): w.destroy()
        self._h_tree = ttk.Treeview(tab, columns=("player","pos","score","date"), show="headings", height=14)
        for c,w in [("player",200),("pos",120),("score",70),("date",150)]:
            self._h_tree.heading(c, text=c.title()); self._h_tree.column(c, width=w)
        self._h_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        ttk.Button(tab, text="Clear", command=lambda: [self._h_tree.delete(i) for i in self._h_tree.get_children()]).pack(pady=(0,6))

    def _save_hist(self, r):
        from datetime import datetime
        if "H" not in self._built: self._build_history_content()
        self._h_tree.insert("", 0, values=(r.player.name, r.player.position.value,
                                            f"{r.overall_score:.0%}",
                                            datetime.now().strftime("%Y-%m-%d %H:%M")))

    def destroy(self):
        self._c_stop(); self._v_stop()
        if self._cam: self._cam.close()
        if self._vid: self._vid.close()
        super().destroy()


def main():
    App().mainloop()

if __name__ == "__main__":
    main()
