import uvicorn
from pathlib import Path
import subprocess
import os
import sys
import ctypes
import ctypes.wintypes
import threading
import time
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.main import app


def _fallback_focus_browser_window_by_title_segments() -> bool:
    if os.name != "nt":
        return False
    title_segments = (
        "Demo | ELT Room Test Data Management",
        "127.0.0.1:8000",
        "ELT Room",
        "Chrome",
    )

    try:
        user32 = ctypes.windll.user32
        enum_windows_proc_type = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.wintypes.HWND,
            ctypes.wintypes.LPARAM,
        )
        user32.EnumWindows.argtypes = [enum_windows_proc_type, ctypes.wintypes.LPARAM]
        user32.EnumWindows.restype = ctypes.c_bool
        user32.IsWindowVisible.argtypes = [ctypes.wintypes.HWND]
        user32.IsWindowVisible.restype = ctypes.c_bool
        user32.GetWindowTextLengthW.argtypes = [ctypes.wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.wintypes.LPWSTR,
            ctypes.c_int,
        ]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = ctypes.c_bool
        user32.SetForegroundWindow.argtypes = [ctypes.wintypes.HWND]
        user32.SetForegroundWindow.restype = ctypes.c_bool

        found_hwnd = ctypes.wintypes.HWND(0)

        def _enum_windows_proc(hwnd, _l_param):
            if not user32.IsWindowVisible(hwnd):
                return True
            title_length = user32.GetWindowTextLengthW(hwnd)
            if title_length <= 0:
                return True
            title_buffer = ctypes.create_unicode_buffer(title_length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
            title_text = title_buffer.value or ""
            if any(title_segment in title_text for title_segment in title_segments):
                found_hwnd.value = hwnd
                return False
            return True

        callback = enum_windows_proc_type(_enum_windows_proc)
        user32.EnumWindows(callback, 0)
        if not found_hwnd.value:
            return False
        user32.ShowWindow(found_hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(found_hwnd)
        return True
    except Exception:
        return False


def _fallback_send_ctrl_alt_r() -> bool:
    if os.name != "nt":
        return False
    try:
        user32 = ctypes.windll.user32
        key_up = 0x0002
        vk_control = 0x11
        vk_alt = 0x12
        vk_r = 0x52
        user32.keybd_event(vk_control, 0, 0, 0)
        user32.keybd_event(vk_alt, 0, 0, 0)
        user32.keybd_event(vk_r, 0, 0, 0)
        user32.keybd_event(vk_r, 0, key_up, 0)
        user32.keybd_event(vk_alt, 0, key_up, 0)
        user32.keybd_event(vk_control, 0, key_up, 0)
        return True
    except Exception:
        return False


def load_bool_mode_from_parent_env(env_key: str, default_value: bool = True) -> bool:
    project_root_path = Path(__file__).resolve().parent
    parent_env_file_path = project_root_path.parent / ".env"

    if not parent_env_file_path.exists():
        parent_env_file_path.write_text(
            "QC_MODE=True\nKIOSK_MODE=True\n",
            encoding="utf-8",
        )
        return default_value

    env_lines = parent_env_file_path.read_text(encoding="utf-8").splitlines()
    found = False
    for env_line in env_lines:
        stripped_line = env_line.strip()
        if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
            continue
        key, value = stripped_line.split("=", 1)
        if key.strip() == env_key:
            found = True
            normalized_value = value.strip().strip('"').strip("'").lower()
            return normalized_value in {"1", "true", "yes", "on"}
    if not found:
        with parent_env_file_path.open("a", encoding="utf-8") as env_file:
            env_file.write(f"\n{env_key}={'True' if default_value else 'False'}\n")
    return default_value


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


def launch_debuggable_chrome(admin_dashboard_url: str, kiosk_mode_enabled: bool) -> None:
    chrome_executable_path = find_chrome_executable_path()
    if chrome_executable_path is None:
        return

    user_data_directory_path = Path(__file__).resolve().parent / ".chrome_qc_profile"
    user_data_directory_path.mkdir(parents=True, exist_ok=True)
    chrome_args = [
        chrome_executable_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={str(user_data_directory_path)}",
    ]
    if kiosk_mode_enabled:
        chrome_args.extend(
            [
                "--kiosk",
                "--disable-save-password-bubble",
                "--disable-features=PasswordManagerOnboarding,PasswordLeakDetection",
            ]
        )
    chrome_args.append(admin_dashboard_url)
    subprocess.Popen(
        chrome_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )


class RestartOnChangeHandler(FileSystemEventHandler):
    def __init__(self, restart_callback: Callable[[Path], None]):
        self.restart_callback = restart_callback
        self._debounce_lock = threading.Lock()
        self._debounce_timer: threading.Timer | None = None

    def on_any_event(self, event) -> None:
        if event.is_directory:
            return
        watched_suffixes = {".py", ".html", ".css", ".js"}
        src_path = Path(getattr(event, "src_path", "") or "")
        dest_path_raw = getattr(event, "dest_path", None)
        dest_path = Path(dest_path_raw) if dest_path_raw else None

        changed_path = None
        if src_path.suffix.lower() in watched_suffixes:
            changed_path = src_path
        elif dest_path is not None and dest_path.suffix.lower() in watched_suffixes:
            changed_path = dest_path
        if changed_path is None:
            return

        with self._debounce_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(
                0.35,
                lambda changed_path=changed_path: self.restart_callback(changed_path),
            )
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

    def trigger_browser_hot_reload_shortcut() -> None:
        used_pk_system_keypress = False
        focused = False
        try:
            from pk_tools.pk_functions.ensure_pressed import ensure_pressed
            used_pk_system_keypress = True
        except Exception:
            used_pk_system_keypress = False

        # pk_system window-focus helpers can raise internal ctypes callback errors
        # on some environments, so keep focus handling on local fallback only.
        focused = _fallback_focus_browser_window_by_title_segments()
        if not focused:
            time.sleep(0.05)

        if used_pk_system_keypress:
            try:
                ensure_pressed("ctrl", "alt", "r")
                return
            except Exception:
                pass

        _fallback_send_ctrl_alt_r()

    def restart_uvicorn_process(changed_path: Path) -> None:
        nonlocal uvicorn_process
        if uvicorn_process.poll() is None:
            uvicorn_process.terminate()
            try:
                uvicorn_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                uvicorn_process.kill()
                uvicorn_process.wait(timeout=5)
        uvicorn_process = spawn_uvicorn_process()
        if changed_path.suffix.lower() in {".js", ".html", ".py"}:
            time.sleep(0.8)
            trigger_browser_hot_reload_shortcut()

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
    qc_mode_enabled = load_bool_mode_from_parent_env("QC_MODE", default_value=True)
    kiosk_mode_enabled = load_bool_mode_from_parent_env("KIOSK_MODE", default_value=True)
    os.environ["QC_MODE"] = "True" if qc_mode_enabled else "False"
    os.environ["KIOSK_MODE"] = "True" if kiosk_mode_enabled else "False"
    if qc_mode_enabled:
        launch_debuggable_chrome(
            "http://127.0.0.1:8000/tester",
            kiosk_mode_enabled=kiosk_mode_enabled,
        )
        run_qc_mode_with_watchdog()
        return
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
