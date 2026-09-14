#!/usr/bin/env python3
"""Keep the deployed Streamlit Community Cloud app awake.

Community Cloud hibernates an app after a period without traffic. A plain HTTP
request is not enough to prevent or reverse that: the app root serves a static
SPA shell that returns 200 whether the app is awake or asleep, so the container
is never contacted and the inactivity timer never resets. Waking a sleeping app
needs a real browser to click the wake button.

This visits the app in headless Chromium, clicks the wake button if the sleep
screen is showing, and confirms the app actually rendered.
"""
import os
import sys
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("STREAMLIT_APP_URL", "").strip().rstrip("/")
# Escape hatch for running against a local Chromium; CI installs its own.
CHROMIUM_PATH = os.environ.get("CHROMIUM_PATH") or None

WAKE_BUTTON = '[data-testid="wakeup-button-viewer"]'
APP_ROOT = '[data-testid="stApp"]'


def log(msg):
    print(msg, flush=True)


def check_health():
    """Query the endpoint that reflects real container state, not the SPA shell.

    Community Cloud routes it under /~/+/; a local or self-hosted Streamlit
    serves it at the bare path. Try both and report the first that answers.
    Diagnostic only — the browser render below is what actually decides.
    """
    for path in ("/~/+/_stcore/health", "/_stcore/health"):
        try:
            with urllib.request.urlopen(APP_URL + path, timeout=30) as resp:
                body = resp.read().decode("utf-8", "replace").strip()
                if body == "ok":
                    return path, resp.status, body
                last = (path, resp.status, body)
        except urllib.error.HTTPError as e:
            last = (path, e.code, f"HTTPError: {e.reason}")
        except Exception as e:
            last = (path, None, f"{type(e).__name__}: {e}")
    return last


def app_rendered(page):
    """The app may render in the top document or inside the Cloud iframe."""
    for frame in page.frames:
        try:
            if frame.query_selector(APP_ROOT):
                return True
        except Exception:
            continue
    return False


def main():
    if not APP_URL:
        log("ERROR: STREAMLIT_APP_URL is not set.")
        log("Set it as a repository variable (Settings > Secrets and variables")
        log("> Actions > Variables) to your app's https://<name>.streamlit.app URL.")
        return 1

    path, status, body = check_health()
    log(f"Health before: {path} status={status} body={body!r}")
    was_healthy = body == "ok"

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM_PATH)
        page = browser.new_page()
        try:
            log(f"Visiting {APP_URL}")
            page.goto(APP_URL, wait_until="domcontentloaded", timeout=90_000)

            wake = page.locator(WAKE_BUTTON)
            try:
                wake.wait_for(state="visible", timeout=10_000)
                log("App was asleep — clicking the wake button.")
                wake.click()
            except Exception:
                log("No wake button present (app was already awake).")

            # Whether we clicked or not, wait for the app itself to appear.
            for _ in range(30):
                if app_rendered(page):
                    log(f"App rendered ({APP_ROOT} found).")
                    break
                page.wait_for_timeout(2_000)
            else:
                log(f"ERROR: {APP_ROOT} never appeared after 60s.")
                return 1

            # Hold the session open briefly so the visit registers as real traffic.
            page.wait_for_timeout(5_000)
        finally:
            browser.close()

    path, status, body = check_health()
    log(f"Health after:  {path} status={status} body={body!r}")

    # The rendered app is the authoritative signal; a health path that does not
    # answer is worth logging but is not a failure on its own.
    log("Already awake." if was_healthy else "Woken.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
