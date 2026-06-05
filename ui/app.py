import streamlit as st
import streamlit.components.v1 as components
import os
import sys
from html import escape as html_escape

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.analyser import get_analyser_pipeline, analyse_batch
# from core.news_agent import check_vendor_history

st.set_page_config(page_title="ClearConsent AI | Risk Scanner", page_icon="⚖️", layout="wide")

if "scan_count" not in st.session_state:
    st.session_state.scan_count = 0

if "user_input" not in st.session_state:
    st.session_state.user_input = ""

MAX_CHARS = 20000  # approx 3000 words
BATCH_SIZE = 5
MAX_CHUNKS_PER_SCAN = 15

@st.cache_resource
def load_backend():
    return get_analyser_pipeline()

with st.spinner("Loading AI Compliance Engine..."):
    vector_store, llm_pipeline = load_backend()

_LOGO_SVG = """<svg width="50" height="58" viewBox="0 0 50 58" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M25 2L3 11v18c0 13 9.5 25 22 28C37.5 54 47 42 47 29V11L25 2z"
        fill="#00A8E8" fill-opacity="0.12" stroke="#00A8E8" stroke-width="1.8"/>
  <path d="M17 29l6 6 10-12" stroke="#00A8E8" stroke-width="2.3"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

_RISK_STYLES = {
    "CRITICAL": {"bg": "rgba(220, 38, 38, 0.15)",  "border": "#dc2626", "label": "#ef4444", "icon": "🚨"},
    "HIGH":     {"bg": "rgba(234, 88, 12, 0.15)",   "border": "#ea580c", "label": "#f97316", "icon": "🟠"},
    "MEDIUM":   {"bg": "rgba(202, 138, 4, 0.15)",   "border": "#ca8a04", "label": "#eab308", "icon": "🟡"},
    "LOW":      {"bg": "rgba(100, 100, 100, 0.12)", "border": "#6b7280", "label": "#9ca3af", "icon": "ℹ️"},
}

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(_LOGO_SVG, unsafe_allow_html=True)
    st.title("ClearConsent AI")
    st.markdown("Instantly flag data rights violations hidden in Terms of Service, Privacy Policies, and EULAs.")
    st.divider()
    st.caption("This tool provides AI-driven risk analysis, not formal legal advice. Laws referenced cover EU and Swiss regulations.")

# ── Main header ───────────────────────────────────────────────────────────────

st.title("Scan Terms & Conditions for Hidden Risks")
st.markdown("Paste any Terms of Service, Privacy Policy, or EULA below to spot compliance issues in seconds.")

st.info("🔍 **Unlike standard AI, this tool doesn't guess.** It retrieves actual GDPR, Swiss nFADP, and EU AI Act statutes and judges your text directly against them — every flag is backed by a real legal citation, not a hallucination.")

# ── Input form ────────────────────────────────────────────────────────────────

def load_bad_example():
    st.session_state.user_input = (
        "By accepting these terms, you agree that we may retain your behavioral data indefinitely "
        "and share it with third-party advertisers in the United States. Your data will also be "
        "used to train our AI models and generative systems."
    )

def load_good_example():
    st.session_state.user_input = (
        "You have the right to request the deletion of your account and all associated personal "
        "data at any time. We will process this request within 30 days. We do not sell your data "
        "to third parties."
    )

st.markdown("**Don't have terms handy? Try an example:**")
colA, colB, colC = st.columns([1, 1, 2.8])
with colA:
    st.button("🚨 Load Aggressive Terms", on_click=load_bad_example)
with colB:
    st.button("✅ Load Safe Terms", on_click=load_good_example)


# st.session_state.vendor_name = st.text_input(
#     "Who is the vendor? (Optional, to check breach history)",
#     placeholder="E.g., Meta, OpenAI, Adobe"
# )

user_text = st.text_area(
    f"Paste terms here (Max {MAX_CHARS:,} characters):",
    value=st.session_state.user_input,
    height=250,
    max_chars=MAX_CHARS,
    placeholder="E.g., We may retain your data indefinitely..."
)

# ── Annotated document builder ────────────────────────────────────────────────

def build_annotated_html(chunks, all_results, all_references):
    LABEL = (
        'font-size:0.68em;font-weight:700;color:#6b7280;'
        'letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px;'
    )
    SEP = 'border-top:1px solid rgba(255,255,255,0.05);'
    ellipsis = (
        '<div style="text-align:center;color:#4a5568;padding:8px 0;'
        'font-size:0.82em;letter-spacing:5px;">· · ·</div>'
    )
    parts = []
    in_safe_run = False

    for i, chunk in enumerate(chunks):
        eval_item = all_results.get(i)
        is_vio = eval_item is not None and eval_item.is_violation

        if is_vio:
            if in_safe_run:
                parts.append(ellipsis)
                in_safe_run = False

            risk_key    = eval_item.risk_level.upper()
            s           = _RISK_STYLES.get(risk_key, _RISK_STYLES["LOW"])
            safe_chunk  = html_escape(chunk).replace("\n", "<br>")
            safe_law    = html_escape(eval_item.violated_law)
            safe_reason = html_escape(eval_item.reason)
            ref         = all_references.get(i, {})
            safe_citation = html_escape(ref.get("matched_law_text", ""))

            parts.append(
                # ── Card shell ──
                f'<div style="border:1px solid {s["border"]};border-radius:8px;'
                f'margin:14px 0;overflow:hidden;font-family:sans-serif;">'

                # ── Header row: risk badge + law name ──
                f'<div style="background:{s["bg"]};padding:10px 16px;'
                f'display:flex;align-items:center;gap:8px;">'
                f'<span style="color:{s["label"]};font-weight:700;font-size:0.88em;">'
                f'{s["icon"]} {risk_key}</span>'
                f'<span style="color:#4a5568;">·</span>'
                f'<span style="color:#a0aec0;font-size:0.82em;font-weight:600;">{safe_law}</span>'
                f'</div>'

                # ── Your document ──
                f'<div style="padding:12px 16px;">'
                f'<div style="{LABEL}">Your Document</div>'
                f'<div style="font-size:0.88em;line-height:1.65;color:#d1d5db;'
                f'font-style:italic;">&ldquo;{safe_chunk}&rdquo;</div>'
                f'</div>'

                # ── Legal citation ──
                f'<div style="padding:12px 16px;{SEP}background:rgba(0,0,0,0.15);">'
                f'<div style="{LABEL}">Legal Citation</div>'
                f'<div style="font-size:0.84em;line-height:1.75;color:#a0aec0;">{safe_citation}</div>'
                f'</div>'

                # ── Analysis ──
                f'<div style="padding:12px 16px;{SEP}">'
                f'<div style="{LABEL}">Why This Is a Violation</div>'
                f'<div style="font-size:0.84em;line-height:1.6;color:#9ca3af;">{safe_reason}</div>'
                f'</div>'

                f'</div>'
            )
        else:
            in_safe_run = True

    if in_safe_run:
        parts.append(ellipsis)

    body = "".join(parts) if parts else (
        '<div style="text-align:center;color:#4a5568;padding:20px;font-size:0.9em;">'
        'No flagged sections — document appears clean.</div>'
    )
    return '<div style="padding:4px 0;">' + body + "</div>"

# ── Scan ──────────────────────────────────────────────────────────────────────

if st.button("Scan for Compliance Risks", type="primary"):
    if st.session_state.scan_count >= 3:
        st.error("🔒 You have reached the maximum of 3 free scans per session. Please contact sales for enterprise access.")
        st.stop()

    st.session_state.scan_count += 1

    if not user_text.strip():
        st.warning("Please paste some text to analyse.")
    else:
        st.divider()
        st.subheader("📋 Scan Results")
        st.caption("🚨 **Critical:** illegal or severely harmful  ·  🟠 **High:** major privacy violation  ·  🟡 **Medium:** aggressive but common practice")

        # Smooth-scroll the Streamlit main container down to the results section
        components.html(
            """<script>
            var el = window.parent.document.querySelector('[data-testid="stMain"]');
            if (el) { el.scrollBy({top: 600, behavior: 'smooth'}); }
            </script>""",
            height=1
        )

        chunks = [c.strip() for c in user_text.split("\n\n") if len(c.strip()) > 50]

        if not chunks:
            st.warning("Text is too short or lacks substantive paragraphs to analyse.")
            st.stop()

        if len(chunks) > MAX_CHUNKS_PER_SCAN:
            st.warning(f"⚠️ Document is very long. We will scan the first {MAX_CHUNKS_PER_SCAN} substantive paragraphs for now.")
            chunks = chunks[:MAX_CHUNKS_PER_SCAN]

        batches = [chunks[i:i + BATCH_SIZE] for i in range(0, len(chunks), BATCH_SIZE)]
        my_bar = st.progress(0, text=f"Analysing {len(chunks)} paragraphs...")

        all_results = {}
        all_references = {}

        for batch_index, batch in enumerate(batches):
            my_bar.progress(
                (batch_index + 1) / len(batches),
                text=f"Scanning batch {batch_index + 1} of {len(batches)} against legal database..."
            )
            start_id = batch_index * BATCH_SIZE

            try:
                result = analyse_batch(batch, start_id, vector_store, llm_pipeline)
                for eval_item in result["evaluations"]:
                    all_results[eval_item.chunk_id] = eval_item
                all_references.update(result["law_references"])

            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower() or "exhausted" in str(e).lower():
                    st.warning("⏳ The AI is pacing itself due to high volume. We scanned what we could! Please run it again in a minute.")
                    break
                else:
                    st.error("⚠️ Minor processing error on this batch, moving to the next...")
                    continue

        my_bar.empty()

        # Tally results
        violations     = [e for e in all_results.values() if e.is_violation]
        risk_count     = len(violations)
        critical_count = sum(1 for e in violations if "CRITICAL" in e.risk_level.upper())
        high_count     = sum(1 for e in violations if "HIGH"     in e.risk_level.upper())
        medium_count   = sum(1 for e in violations if "MEDIUM"   in e.risk_level.upper())
        safe_count     = len(chunks) - risk_count

        # ── Executive summary at top of results ──
        st.subheader("Executive Summary")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Risks Found",     risk_count)
        c2.metric("🚨 Critical",     critical_count)
        c3.metric("🟠 High",         high_count)
        c4.metric("🟡 Medium",       medium_count)
        c5.metric("✅ Safe Clauses", safe_count)

        if risk_count == 0:
            st.success("✅ **Clear to Proceed:** No major compliance risks detected in this text based on current rules.")
        else:
            st.error("⚠️ **Proceed with Caution:** This agreement contains clauses that may violate your privacy rights or European law.")

        # ── Annotated document view ──
        if risk_count > 0:
            st.markdown("---")
            st.markdown("**📄 Document Review**")
            st.markdown(build_annotated_html(chunks, all_results, all_references), unsafe_allow_html=True)

        # ── Vendor background check (disabled) ──
        # if st.session_state.vendor_name.strip():
        #     st.divider()
        #     st.subheader(f"🕵️ Vendor Background Check: {st.session_state.vendor_name}")
        #     with st.spinner("Searching the web for recent data breaches and privacy fines..."):
        #         history_report = check_vendor_history(st.session_state.vendor_name)
        #         if "error" in history_report:
        #             st.warning("Could not reach the search engine at this time.")
        #         elif history_report["found_issues"]:
        #             st.error(f"**Warning: Past Incidents Found**\n\n{history_report['summary']}")
        #         else:
        #             st.success(f"✅ **Clean Record:** {history_report['summary']}")

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.caption("Built by **Alison Meng** · ClearConsent AI · AI-driven analysis, not legal advice.")
