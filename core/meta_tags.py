"""Inject Open Graph / Twitter Card meta tags into Streamlit's index.html.

Streamlit has no API for <head> tags, and Streamlit Community Cloud has no
build step, so the only place to add them is the served index.html inside the
installed streamlit package. This is patched once at app startup; the marker
comment makes it idempotent and any filesystem error is swallowed so the app
never fails because of it.
"""

import os

_MARKER = "<!-- clearconsent-og -->"

_TITLE = "ClearConsent AI — Compliance Scanner"
_DESCRIPTION = (
    "Flag data-rights violations hidden in Terms of Service, Privacy Policies "
    "and EULAs. Every flag backed by a real statute (GDPR, Swiss nFADP, "
    "EU AI Act and more), not a hallucination."
)
_URL = "https://clear-consent.streamlit.app/"
_IMAGE = "https://raw.githubusercontent.com/alisonmeng/clear-consent/main/assets/social-preview.png"

_TAGS = f"""{_MARKER}
<meta property="og:type" content="website">
<meta property="og:site_name" content="ClearConsent AI">
<meta property="og:title" content="{_TITLE}">
<meta property="og:description" content="{_DESCRIPTION}">
<meta property="og:url" content="{_URL}">
<meta property="og:image" content="{_IMAGE}">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="640">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_TITLE}">
<meta name="twitter:description" content="{_DESCRIPTION}">
<meta name="twitter:image" content="{_IMAGE}">
"""


def inject_meta_tags() -> None:
    """Patch Streamlit's static index.html with OG/Twitter tags. Idempotent, never raises."""
    try:
        import streamlit

        index_path = os.path.join(os.path.dirname(streamlit.__file__), "static", "index.html")
        with open(index_path, encoding="utf-8") as f:
            html = f.read()
        if _MARKER in html or "<head>" not in html:
            return
        html = html.replace("<head>", "<head>\n" + _TAGS, 1)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception:
        # Read-only site-packages or an unexpected layout: skip, the app must still run.
        pass
