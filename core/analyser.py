import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate 


load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "chroma_db")

# Output structure
class ClauseEvaluation(BaseModel):
    chunk_id: int = Field(description="The exact ID of the chunk being evaluated")
    is_violation: bool = Field(description="True if the clause violates the regulation, False if safe.")
    risk_level: str = Field(description="CNIL Risk level: Low, Medium, High, or Critical. (Use 'Low' if safe)")
    violated_law: str = Field(description="Name of the specific regulation violated, or 'None'")
    reason: str = Field(description="Short, plain English explanation of why it violates, or why it is safe.")

# Batched process
class BatchEvaluation(BaseModel):
    evaluations: list[ClauseEvaluation]

# Connect ChromaDB and Gemini to set up analysis pipeline
def get_analyser_pipeline():
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    vector_store = Chroma(
        collection_name="compliance_rules",
        embedding_function=embeddings,
        persist_directory=DB_DIR
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0,
        max_output_tokens=800
    )
    structured_llm = llm.with_structured_output(BatchEvaluation)

    return vector_store, structured_llm

# Two step retrieval
def analyse_batch(chunk_batch, start_id, vector_store, structured_llm):
    batch_payload = []
    law_references = {}

    for i, chunk_text in enumerate(chunk_batch):
        chunk_id = start_id + i

        # Add filter layer to ignore irrelevant words -> Move to a separate file later
        keywords = ["data", "privacy", "liability", "agree", "share", "third-party", "delete", "retain", "consent", "cookie", "train", "model", "law", "right", "transfer"]
        if not any(word in chunk_text.lower() for word in keywords):
            continue

        # Match chunk with semantic
        results = vector_store.similarity_search(chunk_text, k=1)

        if results:
            # Extract clause
            matched_rule = results[0]
            comprehensive_law = matched_rule.metadata.get("comprehensive_clause", "No clause found.")
            regulation_name = matched_rule.metadata.get("regulation", "Unknown Law")

            batch_payload.append({
                "chunk_id" : chunk_id,
                "vendor_text": chunk_text,
                "law_to_check_against": f"{regulation_name}: {comprehensive_law}"
            })

            law_references[chunk_id] = {
                "matched_law_name": regulation_name,
                "matched_law_text": comprehensive_law,
                "chunk_text": chunk_text
            }

    if not batch_payload:
        return {"evaluations": [], "law_references": law_references}

    # Prompt LLM
    prompt_template = ChatPromptTemplate.from_template("""
    You are a strictly compliant European & Swiss Data Privacy Officer.
    
    EVALUATE THIS BATCH OR VENDOR CLAUSES:
    {batch_json}
    
    INSTRUCTIONS:
    1. For each item in the JSON array, determine if the vendor_text violates its paired law_to_check_against.
    2. Be critical. If the vendor text is vague, treat it as a risk.
    3. Return your evaluation strictly in the requested list format, matching the chunk_id exactly.
    """)

    formatted_prompt = prompt_template.format(batch_json=json.dumps(batch_payload, indent=2))

    # Evaluate
    batch_eval = structured_llm.invoke(formatted_prompt)

    return {
        "evaluations": batch_eval.evaluations if hasattr(batch_eval, 'evaluations') else batch_eval,
        "law_references": law_references
    }

if __name__ == "__main__":
    print("Initialising AI Analyser...")
    v_store, llm_pipeline = get_analyser_pipeline()

    # Test 1: Obvious violation
    test_batch = [
        "By accepting these terms, you agree that we may retain your behavioral data indefinitely and share it with third-party advertisers in the United States.",
        "You have the right to request the deletion of your account and all associated personal data at any time. We will process this request within 30 days.",
        "Welcome to our website! We hope you enjoy the beautiful design and vibrant community.", # This should be safely ignored by the keyword filter
        "Your data will be used to train our AI models and generative systems."
    ]
    print(f"\nEvaluating Batch of {len(test_batch)} Clauses...\n")

    result = analyse_batch(test_batch, 0, v_store, llm_pipeline)

    print("--- RESULTS ---")

    evals = result.get("evaluations", [])

    if not evals:
        print("No evaluations returned (everything might be filtered out as safe or irrelevant).")
    
    for eval_item in evals:
        print(f"Chunk ID: {eval_item.chunk_id}")
        print(f"Violation: {eval_item.is_violation}")
        print(f"Risk Level: {eval_item.risk_level}")
        print(f"Law: {eval_item.violated_law}")
        print(f"Reason: {eval_item.reason}")
        print("-" * 40)