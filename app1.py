import streamlit as st
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.analyser import get_analyser_pipeline, analyse_batch

st.set_page_config(page_title="AI Compliance Scanner", page_icon="⚖️", layout="wide")

@st.cache_resource
def load_backend():
    return get_analyser_pipeline()

with st.spinner("Loading AI Compliance Engine..."):
    vector_store, llm_pipeline = load_backend()

st.title("Terms & Conditions: Risk Scanner")
st.markdown("Paste vendor terms below to scan against **GDPR, Swiss nFADP, and EU AI Act**.")

user_text = st.text_area("Paste terms here:", height=250, placeholder="E.g., We may retain your data indefinitely...")

# Limit batch size
BATCH_SIZE = 5

# Interact
if st.button("Scan for Compliance Risks", type="primary"):
    if not user_text.strip():
        st.warning("Please past some text to analyse.")
    else:
        st.divider()
        st.subheader("Scan Results")

        chunks = [chunk.strip() for chunk in user_text.split('\n\n') if len(chunk.strip()) > 50]

        if not chunks:
            st.warning("Text is too short to analyse.")

        batches = [chunks[i:i + BATCH_SIZE] for i in range(0, len(chunks), BATCH_SIZE)]
        
        progress_text = f"Scanning {len(batches)} paragraphs in {len(batches)} valid batches..."
        my_bar = st.progress(0, text=progress_text)

        safe_count = 0
        risk_count = 0

        for batch_index, batch in enumerate(batches):
            progress = (batch_index + 1) / len(batches)
            my_bar.progress((batch_index + 1) / len(batches), text=f"Analysing batch {batch_index + 1} of {len(batches)}...")

            start_id = batch_index * BATCH_SIZE

            try:
                result = analyse_batch(batch, start_id, vector_store, llm_pipeline)

                for eval_item in result["evaluations"]:
                    chunk_id = eval_item.chunk_id

                    if eval_item.is_violation:
                        risk_count += 1
                        risk_level = eval_item.risk_level.upper()
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

                        with st.expander(f"{icon} **{risk_level} RISK**: {eval_item.violated_law}", expanded=True):
                            st.markdown(f"**Issue:** {eval_item.reason}")
                            st.markdown(f"> *\"{ref['chunk_text']}\"*")
                            st.caption(f"**Legal Reference:** {ref['matched_law_text']}")

                    else:
                        safe_count += 1

                safe_count += len(batch) - len(result["evaluations"])

            except Exception as e:
                if "429" in str(e) or "quota" in str(e) or "EXHAUSTED" in str(e):
                    st.warning("Service is experiencing high traffic right now. Please try again in a few minutes.")
                    break
                else:
                    st.error("Minor processing error on this batch, moving to the next...")
                    print(e)
                    continue
            
        my_bar.empty()

        st.divider()
        col1, col2 = st.columns(2)
        col1.metric("High/Critical Risks Found", risk_count)
        col2.metric("Compliant/Safe Clauses", safe_count)
        
        if risk_count == 0:
            st.success("No major compliance risks detected in this text based on current rules.")