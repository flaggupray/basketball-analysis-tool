"""Camera capture and recording for shooting form analysis."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class Recording:
    path: Path
    fps: float
    duration: float
    frame_count: int
    resolution: tuple[int, int]


class CameraManager:

    def __init__(self):
        self._cap: cv2.VideoCapture | None = None
        self._recording = False
        self._writer: cv2.VideoWriter | None = None
        self._frame_count = 0
        self._start_time = 0.0
        self._recordings: list[Recording] = []

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def recordings(self) -> list[Recording]:
        return self._recordings

    def open(self, camera_id: int = 0) -> bool:
        self._cap = cv2.VideoCapture(camera_id)
        if not self._cap.isOpened():
            self._cap = None
            return False
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._cap.set(cv2.CAP_PROP_FPS, 30)
        return True

    def close(self):
        if self._recording:
            self.stop_recording()
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def read_frame(self) -> np.ndarray | None:
        if not self.is_open:
            return None
        ret, frame = self._cap.read()
        if not ret:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def start_recording(self, output_dir: str = ".") -> bool:
        if not self.is_open or self._recording:
            return False

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        filename = out_path / f"shooting_{time.strftime('%Y%m%d_%H%M%S')}.mp4"

        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*"avc1")

        self._writer = cv2.VideoWriter(str(filename), fourcc, fps, (w, h))
        if not self._writer.isOpened():
            self._writer = None
            return False

        self._recording = True
        self._frame_count = 0
        self._start_time = time.time()
        self._current_filename = filename
        return True

    def stop_recording(self) -> Recording | None:
        if not self._recording:
            return None

        self._recording = False
        duration = time.time() - self._start_time

        if self._writer is not None:
            self._writer.release()
            self._writer = None

        if not hasattr(self, "_current_filename"):
            return None

        path = self._current_filename
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        rec = Recording(
            path=Path(path),
            fps=fps,
            duration=duration,
            frame_count=self._frame_count,
            resolution=(w, h),
        )
        self._recordings.append(rec)

        # Write the recorded frame to the video file
        return rec

    def write_frame(self, frame: np.ndarray):
        if self._writer is not None and self._recording:
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self._writer.write(bgr)
            self._frame_count += 1

    def preview_frame(self) -> np.ndarray | None:
        frame = self.read_frame()
        if frame is None:
            return None

        h, w = frame.shape[:2]
        preview = frame.copy()

        # Draw recording indicator
        if self._recording:
            elapsed = time.time() - self._start_time
            cv2.circle(preview, (w - 30, 30), 12, (0, 0, 255), -1)
            cv2.putText(preview, f"REC {elapsed:.0f}s", (w - 120, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Draw crosshair for shot alignment
        cx, cy = w // 2, h // 2
        cv2.line(preview, (cx - 40, cy), (cx + 40, cy), (0, 255, 0, 100), 1)
        cv2.line(preview, (cx, cy - 40), (cx, cy + 40), (0, 255, 0, 100), 1)
        cv2.circle(preview, (cx, cy), 5, (0, 255, 0, 100), 1)

        return preview
