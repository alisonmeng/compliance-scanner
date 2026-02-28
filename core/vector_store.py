import os
import json
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "chroma_db")
RULES_FILE = os.path.join(BASE_DIR, "data", "rules.json")

def initialise_vector_store():
    print("Initialising Vecotr Database...")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    try:
        with open(RULES_FILE, "r", encoding="utf-8") as file:
            rules_data = json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find {RULES_FILE}. Please create it first.")
        return None
    
    # Decoupled data
    texts_to_embed = []
    metadatas = []
    ids = []

    for rule in rules_data:
        texts_to_embed.append(rule["semantic_description"])
        ids.append(rule["rule_id"])

        metadatas.append({
            "regulation": rule["regulation"],
            "topic": rule["topic"],
            "risk_level": rule["risk_level"],
            "comprehensive_clause": rule["comprehensive_clause"]
        })

    print(f"Embedding {len(texts_to_embed)} rules into ChromaDB...")

    vector_store = Chroma.from_texts(
        texts=texts_to_embed,
        embedding=embeddings,
        metadatas=metadatas,
        ids=ids,
        persist_directory=DB_DIR,
        collection_name="compliance_rules"
    )

    print(f"Database build successfully and saved locally to: {DB_DIR}")
    return vector_store

def test_database_retrieval(vector_store, test_query):
    print(f"Testing Query: {test_query}")

    results = vector_store.similarity_search(test_query, k=2) # Search top 2 closest matches

    if not results:
        print("No matches found.")
        return
    
    for i, doc in enumerate(results):
        print(f"\n--- Match #{i+1} ---")
        print(f"Matched 'Bait' (Semantic): {doc.page_content}")
        print(f"Retrieved 'Hook' (Law): {doc.metadata.get('comprehensive_clause')}")
        print(f"Risk Level: {doc.metadata.get('risk_level')}")


if __name__ == "__main__":
    v_store = initialise_vector_store()

    if v_store:
        test_input1 = "By using this platform, you grant us permission to keep your files indefinitely on our servers in California to improve our machine learning tools."
        test_input2 = "Identity and Contact Data: Anthropic collects identifiers, including your name, email address, and phone number when you sign up for an Anthropic account, or to receive information on our Services. We may also collect or generate indirect identifiers (e.g., “USER12345”)."
        test_database_retrieval(v_store, test_input2)