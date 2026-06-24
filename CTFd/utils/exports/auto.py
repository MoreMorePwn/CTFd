import datetime
import os
import re
import shutil
import threading
import time
from pathlib import Path

from CTFd.utils import config as ctf_config
from CTFd.utils.dates import ctf_paused, ctftime
from CTFd.utils.exports import export_ctf

AUTO_EXPORT_INTERVAL = 20 * 60
AUTO_EXPORT_MAX_BYTES = 1024 * 1024 * 1024

_auto_export_thread = None
_auto_export_thread_lock = threading.Lock()


def start_auto_exports(app):
    if app.config.get("TESTING"):
        return

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    global _auto_export_thread
    with _auto_export_thread_lock:
        if _auto_export_thread and _auto_export_thread.is_alive():
            return

        _auto_export_thread = threading.Thread(
            target=_auto_export_loop,
            args=(app,),
            daemon=True,
            name="ctfd-auto-export",
        )
        _auto_export_thread.start()


def _auto_export_loop(app):
    while True:
        time.sleep(AUTO_EXPORT_INTERVAL)
        try:
            with app.app_context():
                if ctftime() is False or ctf_paused():
                    continue
                _run_auto_export(app)
        except Exception:
            app.logger.exception("Auto export failed")


def _run_auto_export(app):
    export_dir = Path(app.root_path).parent / ".export"
    export_dir.mkdir(parents=True, exist_ok=True)

    if not _acquire_export_lock(export_dir):
        return

    try:
        _prune_old_exports(export_dir)

        ctf_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", ctf_config.ctf_name()).strip("_")
        ctf_name = ctf_name or "ctfd"
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        target = export_dir / f"{ctf_name}.{timestamp}.zip"

        backup = export_ctf()
        backup.seek(0)
        with target.open("wb") as dst:
            shutil.copyfileobj(backup, dst)
        backup.close()

        _prune_old_exports(export_dir, protected=target)
        app.logger.info("Auto export saved to %s", target)
    finally:
        _release_export_lock(export_dir)


def _acquire_export_lock(export_dir):
    lock_path = export_dir / ".auto_export.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as lock_file:
            lock_file.write(str(os.getpid()))
        return True
    except FileExistsError:
        try:
            if time.time() - lock_path.stat().st_mtime > AUTO_EXPORT_INTERVAL:
                lock_path.unlink()
                return _acquire_export_lock(export_dir)
        except OSError:
            pass
        return False


def _release_export_lock(export_dir):
    try:
        (export_dir / ".auto_export.lock").unlink()
    except FileNotFoundError:
        pass


def _folder_size(path):
    return sum(file.stat().st_size for file in path.glob("*.zip") if file.is_file())


def _prune_old_exports(export_dir, protected=None):
    files = sorted(
        (file for file in export_dir.glob("*.zip") if file.is_file()),
        key=lambda file: file.stat().st_mtime,
    )

    while _folder_size(export_dir) > AUTO_EXPORT_MAX_BYTES and files:
        candidate = files.pop(0)
        if protected and candidate == protected and files:
            files.append(candidate)
            continue
        if protected and candidate == protected:
            return
        candidate.unlink(missing_ok=True)
