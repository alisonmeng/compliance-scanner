import os
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

def check_vendor_history(vendor_name: str):
    """Searches the web for privacy violations related to the vendor."""
    
    # 1. Initialise the free search tool
    search = DuckDuckGoSearchRun()
    
    # 2. Construct a highly targeted search query
    query = f"{vendor_name} company (data breach OR GDPR fine OR privacy lawsuit OR FTC settlement)"
    
    try:
        # Fetch the top snippets from the web
        search_results = search.invoke(query)
    except Exception as e:
        return {"error": "Search engine is currently unavailable."}

    if not search_results or "No good DuckDuckGo Search Result was found" in search_results:
        return {"summary": "No recent data breaches, fines, or major privacy lawsuits found in standard web searches.", "found_issues": False}

    # 3. Initialise Gemini to synthesize the raw search results
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
    
    prompt = PromptTemplate.from_template("""
    You are a Cybersecurity and Data Privacy Investigative Journalist.
    
    I searched the web for privacy violations regarding the company "{vendor_name}".
    Here are the raw search snippets:
    
    <snippets>
    {search_results}
    </snippets>
    
    INSTRUCTIONS:
    1. Read the snippets. Did this company suffer a major data breach, receive a GDPR/privacy fine, or settle a privacy lawsuit?
    2. If YES: Write a 2-3 sentence summary of what happened. Be factual and objective.
    3. If NO: Simply output "CLEAN".
    4. Do not invent information. ONLY use the provided snippets.
    """)
    
    formatted_prompt = prompt.format(vendor_name=vendor_name, search_results=search_results)
    
    # 4. Generate the report
    response = llm.invoke(formatted_prompt).content.strip()
    
    if "CLEAN" in response:
        return {"summary": "No recent data breaches, fines, or major privacy lawsuits found in standard web searches.", "found_issues": False}
    else:
        return {"summary": response, "found_issues": True}

# For local testing
if __name__ == "__main__":
    print("Testing News Agent on a known offender (Meta)...")
    print(check_vendor_history("Meta Facebook"))
    
    print("\nTesting News Agent on a random safe company...")
    print(check_vendor_history("Bob's Local Bakery"))