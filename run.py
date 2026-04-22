import uvicorn
from pathlib import Path
import subprocess
import os
import sys
import threading
import time
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.main import app


def load_qc_mode_from_parent_env() -> bool:
    project_root_path = Path(__file__).resolve().parent
    parent_env_file_path = project_root_path.parent / ".env"

    if not parent_env_file_path.exists():
        parent_env_file_path.write_text("QC_MODE=True\n", encoding="utf-8")
        return True

    env_lines = parent_env_file_path.read_text(encoding="utf-8").splitlines()
    for env_line in env_lines:
        stripped_line = env_line.strip()
        if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
            continue
        key, value = stripped_line.split("=", 1)
        if key.strip() == "QC_MODE":
            normalized_value = value.strip().strip('"').strip("'").lower()
            return normalized_value in {"1", "true", "yes", "on"}

    return True


def find_chrome_executable_path() -> str | None:
    candidate_paths = [
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
    ]
    for candidate_path in candidate_paths:
        if candidate_path.exists():
            return str(candidate_path)
    return None


def launch_debuggable_chrome(admin_dashboard_url: str) -> None:
    chrome_executable_path = find_chrome_executable_path()
    if chrome_executable_path is None:
        return

    user_data_directory_path = Path(__file__).resolve().parent / ".chrome_qc_profile"
    user_data_directory_path.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            chrome_executable_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={str(user_data_directory_path)}",
            admin_dashboard_url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )


class RestartOnChangeHandler(FileSystemEventHandler):
    def __init__(self, restart_callback: Callable[[], None]):
        self.restart_callback = restart_callback
        self._debounce_lock = threading.Lock()
        self._debounce_timer: threading.Timer | None = None

    def on_any_event(self, event) -> None:
        if event.is_directory:
            return
        changed_path = Path(event.src_path)
        if changed_path.suffix.lower() not in {".py", ".html", ".css", ".js"}:
            return

        with self._debounce_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(0.35, self.restart_callback)
            self._debounce_timer.daemon = True
            self._debounce_timer.start()


def spawn_uvicorn_process() -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        shell=False,
    )


def run_qc_mode_with_watchdog() -> None:
    project_root_path = Path(__file__).resolve().parent
    watched_paths = [project_root_path / "app", project_root_path / "run.py"]

    uvicorn_process = spawn_uvicorn_process()

    def restart_uvicorn_process() -> None:
        nonlocal uvicorn_process
        if uvicorn_process.poll() is None:
            uvicorn_process.terminate()
            try:
                uvicorn_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                uvicorn_process.kill()
                uvicorn_process.wait(timeout=5)
        uvicorn_process = spawn_uvicorn_process()

    observer = Observer()
    handler = RestartOnChangeHandler(restart_callback=restart_uvicorn_process)
    for watched_path in watched_paths:
        if watched_path.is_dir():
            observer.schedule(handler, str(watched_path), recursive=True)
        elif watched_path.is_file():
            observer.schedule(handler, str(watched_path.parent), recursive=False)

    observer.start()
    try:
        while True:
            if uvicorn_process.poll() is not None:
                uvicorn_process = spawn_uvicorn_process()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join(timeout=3)
        if uvicorn_process.poll() is None:
            uvicorn_process.terminate()
            try:
                uvicorn_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                uvicorn_process.kill()


def main() -> None:
    qc_mode_enabled = load_qc_mode_from_parent_env()
    os.environ["QC_MODE"] = "True" if qc_mode_enabled else "False"
    if qc_mode_enabled:
        launch_debuggable_chrome("http://127.0.0.1:8000/tester")
        run_qc_mode_with_watchdog()
        return
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
