import streamlit as st
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.analyser import get_analyser_pipeline, analyse_batch

st.set_page_config(page_title="ClearConsent AI | Risk Scanner", page_icon="⚖️", layout="wide")

if "scan_count" not in st.session_state:
    st.session_state.scan_count = 0

 
MAX_CHARS = 20000 # approx 3000 words
user_text = st.text_area("Paste terms here (Max 20,000 characters):", 
                         value=st.session_state.user_input, 
                         height=250, 
                         max_chars=MAX_CHARS)

@st.cache_resource
def load_backend():
    return get_analyser_pipeline()

with st.spinner("Loading AI Compliance Engine..."):
    vector_store, llm_pipeline = load_backend()


with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/6054/6054320.png", width=60) # Placeholder logo
    st.title("About ClearConsent")
    st.markdown("Most Terms & Conditions are designed to be ignored. We highlight what you are actually agreeing to.")
    
    st.divider()
    
    st.subheader("🧠 Why this isn't standard ChatGPT")
    st.markdown("""
    Standard AI hallucinates legal facts. This tool uses a **Retrieval-Augmented Generation (RAG)** architecture. 
    1. It scans your text.
    2. It searches our hardcoded database of **GDPR, Swiss nFADP, and EU AI Act** laws.
    3. It explicitly judges the text against the actual legal statute.
    """)
    
    st.subheader("📊 How to read the results")
    st.markdown("""
    Based on the European **CNIL Risk Framework**:
    * 🚨 **Critical:** Illegal clauses or severe data exploitation (e.g., selling health data).
    * 🟠 **High:** Major privacy intrusions requiring active consent.
    * 🟡 **Medium:** Aggressive, but standard tracking/marketing.
    """)
    
    st.divider()
    st.caption("Disclaimer: This tool provides AI-driven risk analysis, not formal legal advice.")

st.title("⚖️ Scan Terms & Conditions")
st.markdown("Paste a vendor's Terms of Service, Privacy Policy, or EULA below to instantly spot compliance risks and data traps.")


if "user_input" not in st.session_state:
    st.session_state.user_input = ""

def load_bad_example():
    st.session_state.user_input = "By accepting these terms, you agree that we may retain your behavioral data indefinitely and share it with third-party advertisers in the United States. Your data will also be used to train our AI models and generative systems."

def load_good_example():
    st.session_state.user_input = "You have the right to request the deletion of your account and all associated personal data at any time. We will process this request within 30 days. We do not sell your data to third parties."


st.markdown("**Don't have terms handy? Try an example:**")
colA, colB, colC = st.columns([1, 1, 2.8])
with colA:
    st.button("🚨 Load Aggressive Terms", on_click=load_bad_example, width="content")
with colB:
    st.button("✅ Load Safe Terms", on_click=load_good_example, width="content")


user_text = st.text_area("Paste terms here:", value=st.session_state.user_input, height=250, placeholder="E.g., We may retain your data indefinitely...")

# Limit batch size
BATCH_SIZE = 5

# Interact
if st.button("Scan for Compliance Risks", type="primary"):
    if st.session_state.scan_count >= 3:
        st.error("🔒 You have reached the maximum of 3 free scans per session. Please contact sales for enterprise access.")
        st.stop() # Halts execution immediately
    
    # If they pass the check, increment their usage
    st.session_state.scan_count += 1
    if not user_text.strip():
        st.warning("Please paste some text to analyse.")
    else:
        st.divider()
        st.subheader("📊 Scan Results")

        chunks = [chunk.strip() for chunk in user_text.split('\n\n') if len(chunk.strip()) > 50]

        if not chunks:
            st.warning("Text is too short or lacks substantive paragraphs to analyse.")
            st.stop()
        
        MAX_CHUNKS_PER_SCAN = 15
        if len(chunks) > MAX_CHUNKS_PER_SCAN:
            st.warning(f"⚠️ Document is very long. We wil scan the first {MAX_CHUNKS_PER_SCAN} substantive paragraphs for now.")
            chunks = chunks[:MAX_CHUNKS_PER_SCAN] # Drop excess data

        batches = [chunks[i:i + BATCH_SIZE] for i in range(0, len(chunks), BATCH_SIZE)]
        
        progress_text = f"Analysing {len(chunks)} paragraphs..."
        my_bar = st.progress(0, text=progress_text)

        safe_count = 0
        risk_count = 0

        for batch_index, batch in enumerate(batches):
            my_bar.progress((batch_index + 1) / len(batches), text=f"Scanning batch {batch_index + 1} of {len(batches)} against legal database...")
            start_id = batch_index * BATCH_SIZE

            try:
                result = analyse_batch(batch, start_id, vector_store, llm_pipeline)

                for eval_item in result["evaluations"]:
                    chunk_id = eval_item.chunk_id

                    if eval_item.is_violation:
                        risk_count += 1
                        risk_level = eval_item.risk_level.upper()
                        # Correct dictionary access
                        ref = result["law_references"][chunk_id]

                        if "CRITICAL" in risk_level:
                            box_color = "error"
                            icon = "🚨"
                        elif "HIGH" in risk_level:
                            box_color = "warning"
                            icon = "🟠"
                        else:
                            box_color = "info"
                            icon = "🟡"

                        # Correct dot notation for eval_item
                        with st.expander(f"{icon} **{risk_level} RISK**: {eval_item.violated_law}", expanded=True):
                            st.markdown(f"**Issue:** {eval_item.reason}")
                            st.markdown(f"> *\"{ref['chunk_text']}\"*")
                            st.caption(f"**Triggered Law:** {ref['matched_law_text']}")

                    else:
                        safe_count += 1

                safe_count += len(batch) - len(result["evaluations"])

            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower() or "exhausted" in str(e).lower():
                    st.warning("⏳ The AI is pacing itself due to high volume. We scanned what we could! Please run it again in a minute.")
                    break
                else:
                    st.error("⚠️ Minor processing error on this batch, moving to the next...")
                    continue
            
        my_bar.empty()


        st.divider()
        st.subheader("Executive Summary")
        col1, col2 = st.columns(2)
        col1.metric("Risks & Violations Found", risk_count)
        col2.metric("Compliant / Standard Clauses", safe_count)
        
        if risk_count == 0:
            st.success("✅ **Clear to Proceed:** No major compliance risks detected in this text based on current rules.")
        else:
            st.error("⚠️ **Proceed with Caution:** This agreement contains clauses that may violate your privacy rights or European law. Review the expanded items above.")