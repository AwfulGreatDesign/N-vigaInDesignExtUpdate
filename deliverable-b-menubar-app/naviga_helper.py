#!/usr/bin/env python3
"""
Naviga Ad Queue — macOS Menu Bar Helper (Deliverable B)
Clicks the Naviga panel's Refresh button inside InDesign on a timer.
Does not modify any Naviga files.
"""

import json
import os
import time
import threading
import subprocess

import rumps
import Quartz
import AppKit

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "naviga_helper_settings.json")
INDESIGN_BUNDLE = "com.adobe.InDesign"

DEFAULT_SETTINGS = {
    "auto_refresh": False,
    "auto_claim": False,
    "interval_seconds": 10,
}

INTERVAL_OPTIONS = [5, 10, 30, 60]


# ── Settings ─────────────────────────────────────────────────────────────────

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# ── InDesign / Accessibility helpers ─────────────────────────────────────────

def indesign_is_frontmost():
    """Return True if InDesign is the currently active application."""
    active = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
    return active.bundleIdentifier() == INDESIGN_BUNDLE


def get_indesign_pid():
    """Return InDesign's PID, or None if not running."""
    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    for app in apps:
        if app.bundleIdentifier() == INDESIGN_BUNDLE:
            return app.processIdentifier()
    return None


def find_button_by_label_ax(pid, label):
    """
    Walk InDesign's AX tree looking for a button with the given label.
    Returns the AXUIElement if found, else None.
    CEP panels often don't expose HTML buttons in the AX tree — this is
    the primary attempt; coordinate fallback is used if this returns None.
    """
    app_ref = Quartz.AXUIElementCreateApplication(pid)

    def _search(element, depth=0):
        if depth > 12:
            return None
        role = _ax_attr(element, "AXRole")
        title = _ax_attr(element, "AXTitle") or _ax_attr(element, "AXDescription") or ""
        if role == "AXButton" and label.lower() in title.lower():
            return element
        children = _ax_attr(element, "AXChildren") or []
        for child in children:
            result = _search(child, depth + 1)
            if result is not None:
                return result
        return None

    return _search(app_ref)


def _ax_attr(element, attr):
    """Safely read an AX attribute, returning None on failure."""
    err, value = Quartz.AXUIElementCopyAttributeValue(element, attr, None)
    if err == 0:
        return value
    return None


def ax_press(element):
    """Send AXPress action to an AX element."""
    Quartz.AXUIElementPerformAction(element, "AXPress")


def get_indesign_window_frame(pid):
    """
    Return the (x, y, width, height) of InDesign's main window in screen
    coordinates (top-left origin), or None if not found.
    """
    app_ref = Quartz.AXUIElementCreateApplication(pid)
    windows = _ax_attr(app_ref, "AXWindows")
    if not windows:
        return None
    win = windows[0]
    pos_val  = _ax_attr(win, "AXPosition")
    size_val = _ax_attr(win, "AXSize")
    if pos_val is None or size_val is None:
        return None
    x, y = pos_val.x, pos_val.y
    w, h = size_val.width, size_val.height
    return (x, y, w, h)


def click_at_screen_coords(x, y):
    """
    Simulate a mouse click at absolute screen coordinates without
    activating/focusing the target application.
    Uses CGEvent so InDesign stays frontmost.
    """
    pt = Quartz.CGPointMake(x, y)
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)

    down = Quartz.CGEventCreateMouseEvent(src, Quartz.kCGEventLeftMouseDown, pt,
                                          Quartz.kCGMouseButtonLeft)
    up   = Quartz.CGEventCreateMouseEvent(src, Quartz.kCGEventLeftMouseUp,   pt,
                                          Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
    time.sleep(0.05)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)


def click_naviga_refresh(pid):
    """
    Attempt to click the Refresh button.
    Strategy 1: AX tree lookup by label.
    Strategy 2: Coordinate estimate — Refresh button is in the top-right
                of the Naviga panel. Estimated offset from window right edge.
    Returns True if a click was attempted.
    """
    # Strategy 1: AX
    btn = find_button_by_label_ax(pid, "Refresh")
    if btn is not None:
        ax_press(btn)
        return True

    # Strategy 2: Coordinate fallback
    frame = get_indesign_window_frame(pid)
    if frame is None:
        return False
    x, y, w, h = frame
    # Refresh button sits ~115px from right edge, ~30px from top of window
    click_x = x + w - 115
    click_y = y + 30
    click_at_screen_coords(click_x, click_y)
    return True


def click_naviga_assign(pid):
    """
    Attempt to click 'Assign this to me' button.
    Strategy 1: AX tree lookup.
    Strategy 2: Not reliably coordinate-based (button position varies by
                queue content), so Strategy 1 only. Returns False if not found.
    """
    btn = find_button_by_label_ax(pid, "Assign this to me")
    if btn is not None:
        ax_press(btn)
        return True
    return False


# ── Menu Bar App ─────────────────────────────────────────────────────────────

class NavigaHelperApp(rumps.App):

    def __init__(self):
        super().__init__("N⚡", quit_button=None)
        self.settings = load_settings()
        self._timer_thread = None
        self._running = False
        self._last_refresh = None
        self._build_menu()
        if self.settings["auto_refresh"]:
            self._start_timer()

    def _build_menu(self):
        s = self.settings

        self._item_refresh = rumps.MenuItem(
            "Auto-Refresh: " + ("ON" if s["auto_refresh"] else "OFF"),
            callback=self._toggle_refresh
        )
        self._item_claim = rumps.MenuItem(
            "Auto-Claim: " + ("ON" if s["auto_claim"] else "OFF"),
            callback=self._toggle_claim
        )

        interval_menu = rumps.MenuItem("Interval")
        for secs in INTERVAL_OPTIONS:
            label = str(secs) + " seconds" + (" ✓" if secs == s["interval_seconds"] else "")
            interval_menu[label] = rumps.MenuItem(
                label, callback=self._make_interval_cb(secs)
            )
        self._item_interval = interval_menu

        self._item_status = rumps.MenuItem("Status: Idle")
        self._item_status.set_callback(None)

        self.menu = [
            self._item_refresh,
            self._item_claim,
            self._item_interval,
            None,
            self._item_status,
            None,
            rumps.MenuItem("Quit", callback=self._quit),
        ]

    def _make_interval_cb(self, secs):
        def cb(_):
            self.settings["interval_seconds"] = secs
            save_settings(self.settings)
            # Rebuild interval submenu to show checkmark
            self._rebuild_interval_menu()
            if self._running:
                self._start_timer()
        return cb

    def _rebuild_interval_menu(self):
        s = self.settings
        for secs in INTERVAL_OPTIONS:
            label_base = str(secs) + " seconds"
            label_check = label_base + " ✓"
            for key in list(self._item_interval.keys()):
                if label_base in key:
                    self._item_interval[key].title = (
                        label_check if secs == s["interval_seconds"] else label_base
                    )

    def _toggle_refresh(self, _):
        self.settings["auto_refresh"] = not self.settings["auto_refresh"]
        save_settings(self.settings)
        self._item_refresh.title = "Auto-Refresh: " + (
            "ON" if self.settings["auto_refresh"] else "OFF"
        )
        if self.settings["auto_refresh"]:
            self._start_timer()
        else:
            self._stop_timer()
            self._item_status.title = "Status: Idle"

    def _toggle_claim(self, _):
        self.settings["auto_claim"] = not self.settings["auto_claim"]
        save_settings(self.settings)
        self._item_claim.title = "Auto-Claim: " + (
            "ON" if self.settings["auto_claim"] else "OFF"
        )

    def _start_timer(self):
        self._stop_timer()
        self._running = True
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()

    def _stop_timer(self):
        self._running = False

    def _timer_loop(self):
        while self._running:
            interval = self.settings["interval_seconds"]
            time.sleep(interval)
            if not self._running:
                break
            if not indesign_is_frontmost():
                self._item_status.title = "Status: Paused (InDesign not active)"
                continue
            pid = get_indesign_pid()
            if pid is None:
                self._item_status.title = "Status: InDesign not running"
                continue
            clicked = click_naviga_refresh(pid)
            if clicked:
                self._last_refresh = time.time()
                self._item_status.title = "Status: Refreshed just now"
                if self.settings["auto_claim"]:
                    time.sleep(1.5)
                    click_naviga_assign(pid)
            else:
                self._item_status.title = "Status: Could not find Refresh button"

    def _quit(self, _):
        self._stop_timer()
        rumps.quit_application()


if __name__ == "__main__":
    NavigaHelperApp().run()
