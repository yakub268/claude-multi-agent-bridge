#!/usr/bin/env python3
"""
Cowork Client — wires Claude Desktop's Cowork panel into the multi-agent bridge.

Inbound:  cowork_task   { task_id, prompt }
Outbound: cowork_ready  { version, output_dirs, watching }
          cowork_result { task_id, status, files, elapsed_seconds }
          cowork_error  { task_id, error, message }

Usage:
    python cowork_client.py                 # daemon mode
    python cowork_client.py --test-window   # verify window detection
    python cowork_client.py --test-input    # verify input coordinate detection
"""

import argparse
import json
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pyperclip
import requests

# watchdog — optional import with clear error
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_OK = True
except ImportError:
    WATCHDOG_OK = False
    print("❌ watchdog not installed. Run: pip install watchdog")

    # Stub so the class definition below compiles without watchdog
    class FileSystemEventHandler:  # type: ignore
        pass


# pyautogui — optional import with clear error
try:
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.3
    PYAUTOGUI_OK = True
except ImportError:
    PYAUTOGUI_OK = False
    print("❌ pyautogui not installed. Run: pip install pyautogui")

# pygetwindow — optional import
try:
    import pygetwindow as gw

    PYGETWINDOW_OK = True
except ImportError:
    PYGETWINDOW_OK = False


# ---------------------------------------------------------------------------
# Filesystem event handler
# ---------------------------------------------------------------------------


class _OutputWatcherHandler(FileSystemEventHandler):
    """Passes file events back to the owning CoworkClient."""

    def __init__(self, callback):
        super().__init__()
        self._cb = callback

    def on_created(self, event):
        if not event.is_directory:
            self._cb(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._cb(event.src_path)


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------


class CoworkClient:
    """
    Bridge node for Claude Desktop's Cowork panel.

    Architecture
    ────────────
    Bus layer       – send / poll / on / status  (same as CodeClient)
    Window layer    – find_window / activate_window / find_cowork_input / send_to_cowork
    FS watcher      – watchdog.Observer on Downloads + Desktop
    UI worker       – queue.Queue decouples slow UI from bus poll loop
    Daemon loop     – run()
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        bus_url: str = "http://localhost:5001",
        output_dirs: Optional[List[str]] = None,
        poll_interval: float = 2.0,
        task_timeout: float = 300.0,
        settle_delay: float = 2.0,
        input_offset_x: float = 0.5,
        input_offset_y: float = 0.88,
    ):
        self.bus_url = bus_url
        self.client_id = "cowork"
        self.last_timestamp = None
        self.handlers: Dict[str, Callable] = {}

        self.output_dirs = [
            Path(p)
            for p in (
                output_dirs
                or [
                    r"C:\Users\yakub\Downloads",
                    r"C:\Users\yakub\Desktop",
                ]
            )
        ]
        self.poll_interval = poll_interval
        self.task_timeout = task_timeout
        self.settle_delay = settle_delay
        self.input_offset_x = input_offset_x
        self.input_offset_y = input_offset_y

        # Window handle
        self._window = None

        # Pending tasks: task_id -> { prompt, baseline, submitted_at, settle_timer, files }
        self._tasks: Dict[str, Dict] = {}
        self._task_queue: queue.Queue = queue.Queue()  # FIFO pending submissions
        self._active_task_id: Optional[str] = None  # currently running in Cowork
        self._task_lock = threading.Lock()

        # UI worker
        self._ui_queue: queue.Queue = queue.Queue()
        self._ui_thread: Optional[threading.Thread] = None

        # FS observer
        self._observer: Optional[object] = None

    # ── Bus layer ──────────────────────────────────────────────────────────

    def send(self, to: str, msg_type: str, payload: Dict) -> bool:
        try:
            r = requests.post(
                f"{self.bus_url}/api/send",
                json={
                    "from": self.client_id,
                    "to": to,
                    "type": msg_type,
                    "payload": payload,
                },
                timeout=2,
            )
            return r.status_code == 200
        except Exception as e:
            print(f"❌ send failed: {e}")
            return False

    def poll(self) -> List[Dict]:
        try:
            params = {"to": self.client_id}
            if self.last_timestamp:
                params["since"] = self.last_timestamp
            r = requests.get(f"{self.bus_url}/api/messages", params=params, timeout=2)
            if r.status_code == 200:
                msgs = r.json().get("messages", [])
                if msgs:
                    self.last_timestamp = msgs[-1]["timestamp"]
                return msgs
        except Exception as e:
            print(f"❌ poll failed: {e}")
        return []

    def on(self, msg_type: str, handler: Callable):
        self.handlers[msg_type] = handler

    def status(self) -> Dict:
        try:
            r = requests.get(f"{self.bus_url}/api/status", timeout=2)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"❌ status failed: {e}")
        return {"status": "unreachable"}

    # ── Window layer ───────────────────────────────────────────────────────

    def find_window(self) -> bool:
        if not PYGETWINDOW_OK:
            print("⚠️  pygetwindow not available — window detection disabled")
            return False
        windows = gw.getWindowsWithTitle("Claude")
        if windows:
            self._window = windows[0]
            print(
                f"✅ Window found: '{self._window.title}' at {self._window.left},{self._window.top} {self._window.width}x{self._window.height}"
            )
            return True
        print("❌ Claude window not found — is Claude Desktop running?")
        return False

    def activate_window(self) -> bool:
        if not self._window:
            return self.find_window()
        try:
            self._window.activate()
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"⚠️  activate failed ({e}), retrying find...")
            return self.find_window()

    def find_cowork_input(self) -> Optional[tuple]:
        """
        Return (x, y) of Cowork's input box using three strategies.

        Strategy 1: pyautogui.locateOnScreen("cowork_input.png") — user-saved template
        Strategy 2: OCR scan for Cowork placeholder keywords
        Strategy 3: Fixed offset (input_offset_x, input_offset_y) from window bounds
        """
        if not PYAUTOGUI_OK:
            return None

        # Strategy 1 — template image
        template = Path(__file__).parent / "cowork_input.png"
        if template.exists():
            try:
                loc = pyautogui.locateOnScreen(str(template), confidence=0.8)
                if loc:
                    cx, cy = pyautogui.center(loc)
                    print(f"✅ Input found via template at ({cx}, {cy})")
                    return (cx, cy)
            except Exception:
                pass

        # Strategy 2 — OCR keyword scan (only if pytesseract is installed)
        try:
            import pytesseract
            from PIL import Image as PILImage

            screenshot = pyautogui.screenshot()
            text = pytesseract.image_to_string(screenshot.convert("L"))
            keywords = (
                "what would you like",
                "describe your task",
                "cowork",
                "give me a task",
            )
            if any(kw in text.lower() for kw in keywords):
                screen_w, screen_h = pyautogui.size()
                cx = int(screen_w * self.input_offset_x)
                cy = int(screen_h * self.input_offset_y)
                print(f"✅ Input found via OCR keywords at ({cx}, {cy})")
                return (cx, cy)
        except Exception:
            pass

        # Strategy 3 — fixed offset fallback
        if self._window:
            cx = int(self._window.left + self._window.width * self.input_offset_x)
            cy = int(self._window.top + self._window.height * self.input_offset_y)
        else:
            screen_w, screen_h = pyautogui.size()
            cx = int(screen_w * self.input_offset_x)
            cy = int(screen_h * self.input_offset_y)

        print(f"ℹ️  Input fallback offset at ({cx}, {cy})")
        return (cx, cy)

    def send_to_cowork(self, prompt: str) -> bool:
        """Activate window, paste prompt into Cowork input, submit."""
        if not PYAUTOGUI_OK:
            print("❌ pyautogui unavailable — cannot send to Cowork")
            return False

        if not self.activate_window():
            return False

        coords = self.find_cowork_input()
        if not coords:
            return False

        try:
            pyautogui.click(coords[0], coords[1])
            time.sleep(0.3)

            # Clear any existing text
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.press("delete")
            time.sleep(0.1)

            # Paste via clipboard (handles Unicode, avoids key-interval issues)
            pyperclip.copy(prompt)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.3)

            # Submit
            pyautogui.press("enter")
            print(
                f"✅ Submitted to Cowork: {prompt[:60]}{'...' if len(prompt) > 60 else ''}"
            )
            return True

        except Exception as e:
            print(f"❌ send_to_cowork failed: {e}")
            return False

    # ── Filesystem watcher ─────────────────────────────────────────────────

    def _snapshot_output_dirs(self) -> Dict[str, float]:
        """Return {path: mtime} for all files currently in output_dirs."""
        snapshot: Dict[str, float] = {}
        for d in self.output_dirs:
            if d.exists():
                for f in d.iterdir():
                    if f.is_file():
                        snapshot[str(f)] = f.stat().st_mtime
        return snapshot

    def start_output_watcher(self):
        if not WATCHDOG_OK:
            print("⚠️  watchdog unavailable — filesystem watcher disabled")
            return
        self._observer = Observer()
        handler = _OutputWatcherHandler(self._on_file_event)
        for d in self.output_dirs:
            d.mkdir(parents=True, exist_ok=True)
            self._observer.schedule(handler, str(d), recursive=False)
        self._observer.start()
        print(f"👁️  Watching: {[str(d) for d in self.output_dirs]}")

    def _on_file_event(self, file_path: str):
        """Called by watchdog thread on any file created/modified."""
        with self._task_lock:
            if not self._active_task_id:
                return
            task = self._tasks.get(self._active_task_id)
            if not task:
                return

            # Ignore files that existed in the baseline snapshot
            if file_path in task["baseline"]:
                return

            # Attribute file to active task
            if file_path not in task["files"]:
                task["files"].append(file_path)
                print(
                    f"📁 New file attributed to {self._active_task_id}: {Path(file_path).name}"
                )

            # Reset settle timer
            if task.get("settle_timer"):
                task["settle_timer"].cancel()

            t = threading.Timer(
                self.settle_delay, self._complete_task, args=[self._active_task_id]
            )
            task["settle_timer"] = t
            t.start()

    def _register_task(self, task_id: str, prompt: str):
        with self._task_lock:
            baseline = self._snapshot_output_dirs()
            self._tasks[task_id] = {
                "prompt": prompt,
                "baseline": baseline,
                "submitted_at": time.time(),
                "settle_timer": None,
                "files": [],
            }
            self._active_task_id = task_id
        print(f"📝 Task registered: {task_id} (baseline: {len(baseline)} files)")

    def _complete_task(self, task_id: str):
        with self._task_lock:
            task = self._tasks.pop(task_id, None)
            if not task:
                return
            if self._active_task_id == task_id:
                self._active_task_id = None

        elapsed = round(time.time() - task["submitted_at"], 1)
        print(f"✅ Task complete: {task_id} ({len(task['files'])} files, {elapsed}s)")

        self.send(
            "all",
            "cowork_result",
            {
                "task_id": task_id,
                "status": "completed",
                "files": task["files"],
                "elapsed_seconds": elapsed,
            },
        )

        # Kick off next queued task
        self._maybe_submit_next()

    def _expire_stale_tasks(self):
        """Called periodically from daemon loop to time out hung tasks."""
        now = time.time()
        with self._task_lock:
            stale = [
                tid
                for tid, t in self._tasks.items()
                if now - t["submitted_at"] > self.task_timeout
            ]

        for task_id in stale:
            with self._task_lock:
                task = self._tasks.pop(task_id, None)
                if not task:
                    continue
                if self._active_task_id == task_id:
                    self._active_task_id = None
                if task.get("settle_timer"):
                    task["settle_timer"].cancel()

            print(f"⏰ Task timed out: {task_id}")
            self.send(
                "all",
                "cowork_result",
                {
                    "task_id": task_id,
                    "status": "timeout",
                    "files": task.get("files", []),
                    "elapsed_seconds": round(self.task_timeout, 1),
                },
            )
            self._maybe_submit_next()

    def _maybe_submit_next(self):
        """Submit the next queued task if Cowork is idle."""
        with self._task_lock:
            if self._active_task_id:
                return  # still busy
            if self._task_queue.empty():
                return

        try:
            task_id, prompt = self._task_queue.get_nowait()
        except queue.Empty:
            return

        # Enqueue the actual UI work on the UI thread
        self._ui_queue.put((task_id, prompt))

    # ── UI worker thread ───────────────────────────────────────────────────

    def _ui_worker(self):
        """
        Runs in its own thread. Dequeues (task_id, prompt) pairs and
        performs the slow window-activation + clipboard-paste + enter.
        Decouples UI latency from the bus poll loop.
        """
        while True:
            try:
                item = self._ui_queue.get(timeout=1)
            except queue.Empty:
                continue

            if item is None:  # sentinel — shut down
                break

            task_id, prompt = item
            self._register_task(task_id, prompt)

            if not self.send_to_cowork(prompt):
                with self._task_lock:
                    self._tasks.pop(task_id, None)
                    self._active_task_id = None

                self.send(
                    "all",
                    "cowork_error",
                    {
                        "task_id": task_id,
                        "error": "ui_failure",
                        "message": "Could not submit task to Cowork (window / input not found)",
                    },
                )
                self._maybe_submit_next()

    # ── Message handling ───────────────────────────────────────────────────

    def _handle_cowork_task(self, msg: Dict):
        payload = msg.get("payload", {})
        task_id = payload.get("task_id", f"task-{int(time.time())}")
        prompt = payload.get("prompt", "")

        if not prompt:
            self.send(
                msg.get("from", "all"),
                "cowork_error",
                {
                    "task_id": task_id,
                    "error": "empty_prompt",
                    "message": "payload.prompt is required",
                },
            )
            return

        print(
            f"📩 Queued task {task_id}: {prompt[:60]}{'...' if len(prompt) > 60 else ''}"
        )
        self._task_queue.put((task_id, prompt))
        self._maybe_submit_next()

    # ── Daemon loop ────────────────────────────────────────────────────────

    def run(self):
        print("=" * 65)
        print("⚙️   COWORK CLIENT — DAEMON MODE")
        print("=" * 65)
        print(f"Bus:      {self.bus_url}")
        print(f"Watching: {[str(d) for d in self.output_dirs]}")
        print(f"Timeout:  {self.task_timeout}s  Settle: {self.settle_delay}s")
        print("Press Ctrl+C to stop")
        print("=" * 65)

        # Start filesystem watcher
        self.start_output_watcher()

        # Start UI worker thread
        self._ui_thread = threading.Thread(
            target=self._ui_worker, name="cowork-ui", daemon=True
        )
        self._ui_thread.start()

        # Register default message handler
        self.on("cowork_task", self._handle_cowork_task)

        # Announce readiness
        self.send(
            "all",
            "cowork_ready",
            {
                "version": self.VERSION,
                "output_dirs": [str(d) for d in self.output_dirs],
                "watching": WATCHDOG_OK,
            },
        )
        print(
            f"📡 cowork_ready sent (watchdog={'enabled' if WATCHDOG_OK else 'DISABLED'})"
        )

        # Stale-task reaper interval
        last_expire_check = time.time()
        EXPIRE_INTERVAL = 30.0

        try:
            while True:
                msgs = self.poll()
                for msg in msgs:
                    msg_type = msg.get("type")
                    print(f"📨 [{msg.get('from')}→{msg.get('to')}] {msg_type}")
                    if msg_type in self.handlers:
                        try:
                            self.handlers[msg_type](msg)
                        except Exception as e:
                            print(f"❌ Handler error for {msg_type}: {e}")

                # Reap timed-out tasks
                if time.time() - last_expire_check >= EXPIRE_INTERVAL:
                    self._expire_stale_tasks()
                    last_expire_check = time.time()

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        finally:
            if self._observer:
                self._observer.stop()
                self._observer.join()
            # Stop UI worker
            if self._ui_thread:
                self._ui_queue.put(None)
                self._ui_thread.join(timeout=3)


# ── CLI entry-point ────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Cowork Agent Client")
    parser.add_argument("--bus", default="http://localhost:5001", help="Bus URL")
    parser.add_argument(
        "--test-window", action="store_true", help="Test window detection"
    )
    parser.add_argument(
        "--test-input", action="store_true", help="Test input coordinate detection"
    )
    args = parser.parse_args()

    client = CoworkClient(bus_url=args.bus)

    if args.test_window:
        found = client.find_window()
        if not found:
            sys.exit(1)
        sys.exit(0)

    if args.test_input:
        if not client.find_window():
            sys.exit(1)
        coords = client.find_cowork_input()
        if coords:
            print(f"Input coordinates: {coords}")
        else:
            print("❌ Could not determine input coordinates")
            sys.exit(1)
        sys.exit(0)

    client.run()


if __name__ == "__main__":
    main()
