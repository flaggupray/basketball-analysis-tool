"""Video analysis engine for basketball shooting evaluation.

Features:
- Import and playback video files
- Frame-by-frame analysis with slow motion
- Manual shot tracking (make/miss/attempt)
- Shot arc estimation from user-marked ball positions
- Shot chart generation from tracked data
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class ShotEvent:
    frame_idx: int
    timestamp: float
    result: str  # "make", "miss", "attempt"
    ball_position: tuple[float, float] | None = None  # normalized 0-1 coords
    release_angle: float | None = None


@dataclass
class VideoAnalysis:
    path: Path
    duration: float
    fps: float
    frame_count: int
    resolution: tuple[int, int]
    shots: list[ShotEvent] = field(default_factory=list)
    arc_points: list[tuple[float, float]] = field(default_factory=list)

    @property
    def makes(self) -> int:
        return sum(1 for s in self.shots if s.result == "make")

    @property
    def misses(self) -> int:
        return sum(1 for s in self.shots if s.result == "miss")

    @property
    def attempts(self) -> int:
        return sum(1 for s in self.shots if s.result == "attempt")

    @property
    def total_shots(self) -> int:
        return self.makes + self.misses

    @property
    def make_pct(self) -> float:
        total = self.total_shots
        return self.makes / total if total > 0 else 0.0

    @property
    def estimated_avg_angle(self) -> float | None:
        angles = [s.release_angle for s in self.shots if s.release_angle is not None]
        if not angles:
            return None
        return sum(angles) / len(angles)

    @property
    def angle_consistency(self) -> float | None:
        angles = [s.release_angle for s in self.shots if s.release_angle is not None]
        if len(angles) < 2:
            return None
        mean = sum(angles) / len(angles)
        variance = sum((a - mean) ** 2 for a in angles) / len(angles)
        return float(math.sqrt(variance))

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "duration": self.duration,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "resolution": list(self.resolution),
            "total_shots": self.total_shots,
            "makes": self.makes,
            "misses": self.misses,
            "make_pct": self.make_pct,
            "estimated_avg_angle": self.estimated_avg_angle,
            "angle_consistency": self.angle_consistency,
            "shots": [
                {
                    "frame_idx": s.frame_idx,
                    "timestamp": s.timestamp,
                    "result": s.result,
                    "ball_position": s.ball_position,
                    "release_angle": s.release_angle,
                }
                for s in self.shots
            ],
        }


class VideoAnalyzer:

    def __init__(self):
        self._cap: cv2.VideoCapture | None = None
        self._analysis: VideoAnalysis | None = None
        self._current_frame_idx = 0
        self._playback_speed = 1.0
        self._paused = True

    # ── File I/O ───────────────────────────────────────────────

    def load(self, path: str | Path) -> VideoAnalysis | None:
        path = Path(path)
        if not path.exists():
            return None

        self._cap = cv2.VideoCapture(str(path))
        if not self._cap.isOpened():
            self._cap = None
            return None

        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0.0

        self._analysis = VideoAnalysis(
            path=path,
            duration=duration,
            fps=fps,
            frame_count=frame_count,
            resolution=(w, h),
        )
        self._current_frame_idx = 0
        self._paused = True
        return self._analysis

    def close(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def analysis(self) -> VideoAnalysis | None:
        return self._analysis

    # ── Playback ───────────────────────────────────────────────

    @property
    def current_frame_idx(self) -> int:
        return self._current_frame_idx

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def playback_speed(self) -> float:
        return self._playback_speed

    def set_playback_speed(self, speed: float):
        self._playback_speed = max(0.1, min(speed, 4.0))

    def toggle_pause(self):
        self._paused = not self._paused

    def seek(self, frame_idx: int):
        if self._cap is not None and self._analysis is not None:
            idx = max(0, min(frame_idx, self._analysis.frame_count - 1))
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            self._current_frame_idx = idx

    def seek_relative(self, delta: int):
        self.seek(self._current_frame_idx + delta)

    def get_frame(self) -> np.ndarray | None:
        if self._cap is None:
            return None

        if not self._paused:
            frames_to_skip = max(1, int(self._playback_speed))
            for _ in range(frames_to_skip - 1):
                self._cap.read()
            self._current_frame_idx += frames_to_skip

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame_idx)
        ret, frame = self._cap.read()
        if not ret:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def get_annotated_frame(self) -> np.ndarray | None:
        frame = self.get_frame()
        if frame is None or self._analysis is None:
            return frame

        h, w = frame.shape[:2]
        result = frame.copy()

        # Draw shot markers on current frame
        current_shots = [
            s for s in self._analysis.shots
            if abs(s.frame_idx - self._current_frame_idx) <= 3
        ]
        for s in current_shots:
            if s.ball_position is not None:
                px = int(s.ball_position[0] * w)
                py = int(s.ball_position[1] * h)
                color = (0, 255, 0) if s.result == "make" else (
                    (0, 0, 255) if s.result == "miss" else (255, 200, 0))
                cv2.circle(result, (px, py), 12, color, 2)
                cv2.putText(result, s.result.upper(),
                            (px + 15, py - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Draw arc points
        for i, (ax, ay) in enumerate(self._analysis.arc_points):
            px = int(ax * w)
            py = int(ay * h)
            cv2.circle(result, (px, py), 4, (255, 150, 0), -1)
            if i > 0:
                px2 = int(self._analysis.arc_points[i - 1][0] * w)
                py2 = int(self._analysis.arc_points[i - 1][1] * h)
                cv2.line(result, (px2, py2), (px, py), (255, 150, 0), 2)

        # HUD overlay
        ts = self._current_frame_idx / max(self._analysis.fps, 1)
        hud_lines = [
            f"Time: {ts:.1f}s / {self._analysis.duration:.1f}s",
            f"Frame: {self._current_frame_idx} / {self._analysis.frame_count}",
            f"Speed: {self._playback_speed:.1f}x {'(PAUSED)' if self._paused else ''}",
            f"Shots: {self._analysis.total_shots} ({self._analysis.makes}M/{self._analysis.misses}X)",
        ]
        y0 = 30
        for i, line in enumerate(hud_lines):
            cv2.putText(result, line, (10, y0 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
                        cv2.LINE_AA)

        return result

    # ── Shot Tracking ──────────────────────────────────────────

    def mark_shot(self, result: str, ball_pos: tuple[float, float] | None = None):
        if self._analysis is None:
            return

        ts = self._current_frame_idx / max(self._analysis.fps, 1)
        shot = ShotEvent(
            frame_idx=self._current_frame_idx,
            timestamp=ts,
            result=result,
            ball_position=ball_pos,
        )
        self._analysis.shots.append(shot)

    def mark_arc_point(self, pos: tuple[float, float]):
        if self._analysis is None:
            return
        self._analysis.arc_points.append(pos)

    def clear_arc_points(self):
        if self._analysis is not None:
            self._analysis.arc_points.clear()

    def estimate_release_angle(self, shot_idx: int) -> float | None:
        if self._analysis is None or len(self._analysis.arc_points) < 2:
            return None

        # Use first two arc points to estimate release angle
        p1 = self._analysis.arc_points[0]
        p2 = self._analysis.arc_points[-1]
        dx = p2[0] - p1[0]
        dy = p1[1] - p2[1]  # inverted Y (screen coords)

        if dx == 0:
            angle_rad = math.pi / 2
        else:
            angle_rad = math.atan2(dy, abs(dx))

        angle_deg = math.degrees(angle_rad)
        angle_deg = max(30, min(angle_deg, 65))

        if 0 <= shot_idx < len(self._analysis.shots):
            self._analysis.shots[shot_idx].release_angle = angle_deg

        return angle_deg

    def undo_last_shot(self):
        if self._analysis and self._analysis.shots:
            self._analysis.shots.pop()

    # ── Export ─────────────────────────────────────────────────

    def export_analysis(self, output_path: str | Path):
        if self._analysis is None:
            return
        with open(output_path, "w") as f:
            json.dump(self._analysis.to_dict(), f, indent=2)

    def load_analysis(self, input_path: str | Path) -> VideoAnalysis | None:
        with open(input_path) as f:
            data = json.load(f)

        analysis = VideoAnalysis(
            path=Path(data["path"]),
            duration=data["duration"],
            fps=data["fps"],
            frame_count=data["frame_count"],
            resolution=tuple(data["resolution"]),
        )
        for s in data.get("shots", []):
            analysis.shots.append(ShotEvent(
                frame_idx=s["frame_idx"],
                timestamp=s["timestamp"],
                result=s["result"],
                ball_position=tuple(s["ball_position"]) if s.get("ball_position") else None,
                release_angle=s.get("release_angle"),
            ))
        analysis.arc_points = [
            tuple(p) for p in data.get("arc_points", [])
        ]
        self._analysis = analysis
        return analysis

    # ── Shot Consistency Analysis ──────────────────────────────

    def get_consistency_report(self) -> dict:
        if self._analysis is None or self._analysis.total_shots == 0:
            return {"error": "No shots tracked"}

        a = self._analysis
        report = {
            "total_shots": a.total_shots,
            "makes": a.makes,
            "misses": a.misses,
            "make_pct": a.make_pct,
            "avg_release_angle": a.estimated_avg_angle,
            "angle_consistency_std": a.angle_consistency,
        }

        # Grade consistency
        if a.angle_consistency is not None:
            if a.angle_consistency < 3:
                report["consistency_grade"] = "Excellent"
            elif a.angle_consistency < 6:
                report["consistency_grade"] = "Good"
            elif a.angle_consistency < 10:
                report["consistency_grade"] = "Needs Work"
            else:
                report["consistency_grade"] = "Inconsistent"

        # Grade angle
        if a.estimated_avg_angle is not None:
            ang = a.estimated_avg_angle
            if 45 <= ang <= 52:
                report["angle_grade"] = "Optimal"
            elif 40 <= ang <= 55:
                report["angle_grade"] = "Near Optimal"
            elif ang < 40:
                report["angle_grade"] = "Too Flat"
            else:
                report["angle_grade"] = "Too High"

        # Grade shooting
        if a.total_shots >= 10:
            if a.make_pct >= 0.75:
                report["shooting_grade"] = "Elite"
            elif a.make_pct >= 0.60:
                report["shooting_grade"] = "Solid"
            elif a.make_pct >= 0.45:
                report["shooting_grade"] = "Developing"
            else:
                report["shooting_grade"] = "Needs Work"

        return report
