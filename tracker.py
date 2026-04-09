import time
import sys
import signal
import logging
import os
from datetime import datetime

try:
    from AppKit import NSWorkspace, NSScreen
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
        kCGWindowOwnerName,
        kCGWindowName,
        kCGWindowBounds,
        kCGWindowLayer,
    )
except ImportError:
    print("ERROR: pyobjc が必要です: pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz")
    sys.exit(1)

from db import init_db, insert_activity, insert_switch
from classifier import classify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.expanduser("~/tracker.log")),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

SAMPLE_INTERVAL = 1
API_CLASSIFY_INTERVAL = 5
_running = True

def signal_handler(sig, frame):
    global _running
    log.info("停止シグナル受信")
    _running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_screens():
    screens = []
    ns_screens = NSScreen.screens()
    main_frame = NSScreen.mainScreen().frame()
    for i, screen in enumerate(ns_screens):
        frame = screen.frame()
        is_main = (frame.origin.x == main_frame.origin.x and
                   frame.origin.y == main_frame.origin.y)
        screens.append({"id": i, "label": "main" if is_main else f"sub{i}", "frame": frame})
    return screens

def get_window_screen(window_bounds, screens):
    if not window_bounds:
        return 0, "main"
    win_cx = window_bounds.get("X", 0) + window_bounds.get("Width", 0) / 2
    win_cy = window_bounds.get("Y", 0) + window_bounds.get("Height", 0) / 2
    for screen in screens:
        f = screen["frame"]
        if (f.origin.x <= win_cx <= f.origin.x + f.size.width and
                f.origin.y <= win_cy <= f.origin.y + f.size.height):
            return screen["id"], screen["label"]
    return 0, "main"

def get_active_window():
    screens = get_screens()
    ws = NSWorkspace.sharedWorkspace()
    active_app = ws.activeApplication()
    app_name = active_app.get("NSApplicationName", "不明") if active_app else "不明"
    window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    window_title = ""
    bounds = {}
    if window_list:
        for win in window_list:
            if win.get(kCGWindowOwnerName, "") == app_name and win.get(kCGWindowLayer, 99) == 0:
                window_title = win.get(kCGWindowName, "") or ""
                bounds = dict(win.get(kCGWindowBounds, {}))
                break
    screen_id, screen_label = get_window_screen(bounds, screens)
    return {"app_name": app_name, "window_title": window_title,
            "screen_id": screen_id, "screen_label": screen_label}

def main():
    log.info("=== 作業トラッカー 起動 ===")
    for s in get_screens():
        f = s["frame"]
        log.info(f"  [{s['label']}] {f.size.width:.0f}x{f.size.height:.0f}")
    init_db()
    prev_app, prev_screen, tick = None, None, 0
    while _running:
        try:
            info = get_active_window()
            app, title = info["app_name"], info["window_title"]
            screen_id, screen_label = info["screen_id"], info["screen_label"]
            if prev_app is not None and (app != prev_app or screen_id != prev_screen):
                insert_switch(prev_app, app, prev_screen or 0, screen_id)
                if app != prev_app:
                    log.info(f"切替: {prev_app} → {app} [{screen_label}]")
            use_api = (tick % API_CLASSIFY_INTERVAL == 0)
            category, focus_score = classify(app, title, use_api=use_api)
            insert_activity(app, title, screen_id, screen_label,
                            task_category=category, focus_score=focus_score)
            prev_app, prev_screen = app, screen_id
            tick += 1
        except Exception as e:
            log.error(f"記録エラー: {e}")
        time.sleep(SAMPLE_INTERVAL)
    log.info("=== 停止 ===")

if __name__ == "__main__":
    main()
