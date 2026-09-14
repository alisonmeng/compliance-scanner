<a id="readme-top"></a>
<br />
<div align="center">
  <h1 align="center">⚖️ ClearConsent AI</h1>

  <p align="center">
    A RAG-powered compliance scanner that flags data-rights violations hidden in
    Terms of Service, Privacy Policies, and EULAs — every flag backed by a real
    statute, not a hallucination.
    <br />
    <a href="#usage">View Demo</a>
    ·
    <a href="https://github.com/alisonmeng/compliance-scanner/issues">Report Bug</a>
    ·
    <a href="https://github.com/alisonmeng/compliance-scanner/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#how-it-works">How It Works</a></li>
        <li><a href="#regulations-covered">Regulations Covered</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#evaluation--accuracy">Evaluation &amp; Accuracy</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#project-structure">Project Structure</a></li>
    <li><a href="#adding-or-editing-rules">Adding or Editing Rules</a></li>
    <li><a href="#design-decisions--tradeoffs">Design Decisions &amp; Tradeoffs</a></li>
    <li><a href="#risks--limitations">Risks &amp; Limitations</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

## About The Project

Nobody reads the terms. The clauses that matter — indefinite retention, data sold
to third parties, your files used to train someone's model, a liability waiver for
their own breach — are buried in twelve pages of boilerplate written to be skimmed
past.

**ClearConsent AI** reads them for you. Paste any Terms of Service, Privacy Policy,
or EULA and it returns an annotated document: each risky paragraph highlighted, tagged
with a risk level, and paired with the actual text of the regulation it appears to
violate.

The important part is what it *doesn't* do. It doesn't ask a language model what it
thinks the law says. It retrieves the statute from a vector database of hand-curated
legal rules and asks the model to judge one specific clause against one specific law.
Every flag carries a citation you can check.

> ⚠️ This tool provides AI-driven risk analysis, **not formal legal advice**.

### How It Works

```
Pasted text
  → split on blank lines into paragraphs (min. 50 chars, max 15 per scan)
  → keyword pre-filter drops non-legal prose
  → ChromaDB similarity search over 23 embedded rules
  → matched statute + clause sent to Gemini in batches of 5
  → Pydantic-validated verdict: violation? risk level? which law? why?
  → annotated card view with the legal citation inline
```

Each rule in [`data/rules.json`](data/rules.json) carries two separate pieces of text,
and the split is deliberate:

- **`semantic_description`** — plain-language phrasing of how the violation *tends to
  appear in the wild*. This is what gets embedded, so retrieval matches vendor
  language rather than statutory language.
- **`comprehensive_clause`** — the dense legal text. Never embedded, only handed to
  the LLM once a match is found, so the judgment is grounded in the real wording.

Structured output is enforced with Pydantic (`ClauseEvaluation` / `BatchEvaluation`
in [`core/analyser.py`](core/analyser.py)), so the model cannot return malformed or
invented JSON.

### Regulations Covered

23 rules across 9 instruments of EU and Swiss law:

| Regulation | Rules | Example coverage |
| --- | --- | --- |
| **GDPR** | 12 | Data minimization, forced consent, right to erasure, international transfers, sensitive data, purpose limitation, access & portability, breach notification, processor liability, automated decision-making, children's consent, direct marketing |
| **Swiss nFADP** | 2 (+2 shared) | High-risk profiling, cross-border disclosure |
| **EU AI Act** | 2 | AI training-data governance, AI interaction transparency |
| **ePrivacy Directive** | 1 | Cookies & device tracking |
| **EU Data Act** | 1 | IoT device data rights |
| **Unfair Contract Terms Directive** | 2 | Unilateral modification, forced arbitration & class-action waivers |
| **Digital Services Act** | 1 | Account termination & shadowbanning |
| **Consumer Rights Directive** | 1 | Subscription traps & dark patterns |
| **General consumer law** | 1 | Data-breach liability waivers |

Risk levels follow CNIL conventions: `Critical`, `High`, `Medium`, `Low`. Each rule
also stores its `source_url` and an `exceptions` field, so lawful uses (e.g. tax
retention obligations) aren't flagged as violations.

### Built With

* [![Python][Python-badge]][Python-url]
* [![Streamlit][Streamlit-badge]][Streamlit-url]
* [![LangChain][LangChain-badge]][LangChain-url]
* [![Google Gemini][Gemini-badge]][Gemini-url]
* [![ChromaDB][Chroma-badge]][Chroma-url]

Models: `gemini-2.5-flash-lite` for judgment, `gemini-embedding-001` for retrieval.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Evaluation & Accuracy

**This system has not been benchmarked against a labeled dataset. Nothing below is a
measured accuracy figure, and it should not be read as one.**

That is the single largest gap in the project, and it is deliberately stated up front
rather than buried, because a compliance tool that can't quantify its own false-negative
rate is not yet a compliance tool — it's a prototype.

### What has actually been assessed

A structural audit of the retrieval path, written up in
[`rag_evaluation.md`](rag_evaluation.md). The method was manual: reading each of the 23
rules against the code path that retrieves it, and tracing which rules the pre-filter and
`k=1` search can never surface. That audit is reproducible by inspection and it found
three concrete defects:

| Finding | Evidence | Status |
| --- | --- | --- |
| Only one rule is ever evaluated per paragraph | `similarity_search(k=1)` in [`core/analyser.py`](core/analyser.py) | Confirmed by code inspection |
| 7 of 23 rules are unreachable for many clauses | The 15-word keyword whitelist contains no term matching arbitration, children, cancellation, termination, or profiling language | Confirmed by cross-referencing the whitelist against every rule's topic |
| A weak match is treated identically to a strong one | No similarity threshold; `k=1` always returns a result | Confirmed by code inspection |

The "40–60% of multi-violation clauses under-reported" figure in the audit is an
**unvalidated estimate** from manual review of sample clauses, not a measurement. It is
useful for prioritization and worthless as a claim.

### What is not measured

No labeled corpus. No precision or recall. No false-positive rate on benign clauses. No
second reviewer, so no check on whether the rule-to-clause labels reflect anything beyond
one person's reading.

### The harness that would fix this

Planned as the next unit of work, ahead of any retrieval change — because without a
baseline there is no way to prove a fix helped:

1. **Corpus** — 30–50 real published policies, paragraph-split, each paragraph labeled
   with the set of `rule_id`s it violates (empty set for benign paragraphs). Real
   documents, not synthetic ones, so the keyword-filter blind spots show up.
2. **Retrieval metrics** — recall@k and MRR for the vector search alone, measured
   separately from the LLM. Isolating these matters: a miss caused by retrieval and a
   miss caused by judgment need different fixes.
3. **End-to-end metrics** — precision, recall, and per-severity confusion on the final
   verdicts, with false positives on benign text tracked separately since those are what
   destroy user trust fastest.
4. **Regression gate** — the corpus runs on every change to `rules.json` or the retrieval
   path, so widening a `semantic_description` can't silently degrade another rule.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

### Prerequisites

* Python 3.10+
* A Google AI Studio API key — free tier is sufficient
  ([get one here](https://aistudio.google.com/app/apikey))

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/alisonmeng/compliance-scanner.git
   cd compliance-scanner
   ```
2. Create a virtual environment and install dependencies
   ```sh
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Add your API key to a `.env` file in the project root
   ```sh
   echo "GOOGLE_API_KEY=your_key_here" > .env
   ```
4. *(Optional)* Rebuild the vector database. A prebuilt `chroma_db/` is committed, so
   this is only needed after editing `data/rules.json`.
   ```sh
   python -m core.vector_store
   ```
5. Launch the app
   ```sh
   streamlit run ui/app.py
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

Open the app, paste a document into the text area, and hit **Scan for Compliance
Risks**. Two example documents are one click away — *Load Aggressive Terms* and
*Load Safe Terms* — if you want to see both outcomes without hunting for a policy.

Results come back in two parts:

**Executive summary** — a count of total risks broken down by severity, plus safe
clauses, and a verdict banner.

**Document review** — one card per flagged paragraph, each showing:

| Section | Contents |
| --- | --- |
| Header | Risk badge (🚨 Critical / 🟠 High / 🟡 Medium) and the regulation name |
| Your Document | The exact paragraph from your text |
| Legal Citation | The full statutory clause it was matched against |
| Why This Is a Violation | Plain-English explanation from the model |

Clean paragraphs are collapsed into `· · ·` separators so the flagged sections stand out.

**Current limits:** 20,000 characters per document, the first 15 substantive
paragraphs per scan, and 3 scans per browser session. Rate-limit errors from the API
are caught and surfaced as a "try again in a minute" notice rather than a crash.

You can also run either backend module standalone for a quick check:

```sh
python -m core.analyser      # runs a 4-clause test batch
python -m core.news_agent    # tests the vendor background check
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Project Structure

```
compliance-scanner/
├── core/
│   ├── analyser.py       # Retrieval + LLM judgment pipeline
│   ├── vector_store.py   # Builds the ChromaDB collection from rules.json
│   └── news_agent.py     # Vendor breach-history search (built, not yet wired in)
├── data/
│   └── rules.json        # 23 curated legal rules — the knowledge base
├── ui/
│   └── app.py            # Streamlit interface
├── chroma_db/            # Prebuilt vector store (committed)
├── .streamlit/
│   └── config.toml       # Dark theme + headless server config
├── rag_evaluation.md     # Retrieval quality audit and fix priorities
└── requirements.txt
```

**A note on `news_agent.py` — built, working, deliberately not shipped.** It searches
DuckDuckGo for a vendor's breach, fine, and lawsuit history and has Gemini summarize the
findings, instructed to output `CLEAN` rather than speculate when the snippets don't
support a claim. It runs standalone today; the UI hooks are commented out in
[`ui/app.py`](ui/app.py).

It's held back because it's the highest-liability surface in the project: it makes
factual assertions about named companies, sourced from unranked search snippets, with no
provenance shown to the user. Shipping it requires three things first — per-claim source
links surfaced in the UI, a confidence floor below which it reports nothing rather than
guessing, and a false-positive check against a set of companies with no incident history.
Until those exist, the cost of one confidently wrong accusation outweighs the feature.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Adding or Editing Rules

The knowledge base is a plain JSON array — no code changes needed to extend it.
Add an object with all eight fields:

```json
{
  "rule_id": "GDPR_ART06_LEGITIMATE",
  "regulation": "GDPR",
  "topic": "Legitimate Interests",
  "risk_level": "High",
  "source_url": "https://gdpr-info.eu/art-6-gdpr/",
  "semantic_description": "How this violation actually reads in a vendor's terms — this text gets embedded",
  "comprehensive_clause": "The dense legal text sent to the LLM once a match is found",
  "exceptions": "Lawful uses that should not be flagged"
}
```

Then rebuild the vector store so the new rule is searchable:

```sh
python -m core.vector_store
```

Write `semantic_description` the way a company's lawyer would phrase the clause, not
the way the statute phrases it — that field is doing all the retrieval work.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Design Decisions & Tradeoffs

Every choice below bought something and cost something. The cost column is the honest half.

| Decision | Why | What it costs |
| --- | --- | --- |
| **Split each rule into `semantic_description` (embedded) and `comprehensive_clause` (sent to the LLM)** | Vendor terms and statutory text don't share vocabulary. Embedding the statute would match on legal register rather than meaning; embedding the paraphrase matches how violations actually read. The model still sees the real law. | Two fields to maintain per rule, and retrieval quality now depends on how well a human predicted the phrasing a vendor would use. A bad paraphrase silently disables a rule. |
| **Keyword pre-filter before vector search** | Skips the embedding call entirely for prose with no legal content. On a real policy, most paragraphs are boilerplate. Cuts cost and latency. | A hardcoded 15-word whitelist is a recall bug, not an optimization. It currently blocks 7 of 23 rules. Should be derived from the rules themselves, not hand-typed. |
| **`gemini-2.5-flash-lite` at `temperature=0`, 800 max output tokens** | Cheapest tier that reliably fills a structured schema. Temperature 0 for reproducibility — the same clause should get the same verdict twice. | Weaker legal reasoning than a frontier model on genuinely ambiguous clauses. Untested assumption: no A/B against a larger model has been run, so the quality gap is unquantified. |
| **Pydantic structured output over prompt-and-parse** | The schema is enforced by the API, so a malformed or hallucinated response fails loudly instead of corrupting the results table. | Constrains the model to a fixed verdict shape. It can't express "this violates three rules" or "this is unclear" — the schema itself contributes to the under-reporting problem. |
| **Local ChromaDB, persisted to disk and committed to git** | 23 rules don't justify a hosted vector database. Committing the built index means the app starts with zero setup and no embedding cost on first run. | Binary artifacts in version control. The index can drift from `rules.json` with nothing to catch it — there's no build check that they match. Won't survive past a few thousand rules. |
| **Batching 5 paragraphs per LLM call** | Amortizes per-request overhead and keeps the app under free-tier rate limits. | One failed call loses five paragraphs, not one. Failures degrade in chunks. |
| **Hard caps: 20k chars, 15 paragraphs, 3 scans per session** | Bounds worst-case cost per user on a free API tier and keeps scan time tolerable. | Real privacy policies routinely exceed 15 substantive paragraphs, so a full document is silently truncated. This is a demo constraint, not a product one. |
| **Streamlit** | Fastest path from working pipeline to something a non-technical person can use. | Server-rendered, session-scoped state, and violation cards built as inline-styled HTML strings. Fine at this size; not a foundation for a real front end. |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Risks & Limitations

### Users paste confidential documents into a third-party API

The most serious issue, and the one most easily missed given what this tool is for.
Pasted text is sent to Google's Gemini API. Anyone scanning an unsigned contract, an
NDA, or a vendor agreement under review is disclosing it to a processor they didn't
choose and weren't told about. There is currently no data-handling notice in the UI, no
retention statement, and no self-hosted inference option. **A tool that flags GDPR
violations should not create one.** Minimum fix: an explicit pre-scan disclosure naming
the processor; proper fix: a local-model option for sensitive documents.

### Legal exposure

Output names specific regulations and asserts violations. The disclaimer covers the
obvious case, but the presentation — statutory citations, severity badges, formal
verdicts — invites more reliance than a single caption offsets. Real deployment would
need the disclaimer at the point of each result, not only in the sidebar and footer.

### Known false-negative bias

By construction, this tool under-reports. `k=1` means one violation per paragraph
regardless of how many are present, the keyword filter drops paragraphs before they're
ever searched, and the response schema has no way to express multiple violations. A
clean scan is currently weak evidence of a clean document, and the UI does not say so.

### Operational and dependency risk

Single-provider dependency on Google for both embeddings and inference, with a model
(`flash-lite`) on a fast deprecation cadence — a retirement forces re-embedding the
entire index and re-validating verdicts. Cost per scan is not instrumented. No error
monitoring, no logging, no usage telemetry.

### Coverage

EU and Swiss law only. No CCPA, PIPEDA, UK GDPR, or PECR, so a US or UK document will
scan as cleaner than it is. Coverage is 23 rules against instruments containing
hundreds of obligations — the selection is opinionated toward commonly abused consumer
clauses, and absence of a flag says nothing about the rest.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Roadmap

Sequenced, not listed. The ordering is the point: the measurement work comes before the
retrieval fixes, because every fix in Phase 2 is a recall improvement that cannot be
proven without a baseline to compare against. Shipping those fixes first would mean
changing the system and having no way to know whether it got better.

**Shipped**

- [x] 23-rule knowledge base across GDPR, nFADP, EU AI Act, ePrivacy, UCTD, DSA, CRD
- [x] Two-field rule design — embed the paraphrase, cite the statute
- [x] Pydantic-enforced structured output
- [x] Batched analysis with graceful rate-limit degradation
- [x] Annotated document view with inline legal citations
- [x] Retrieval audit identifying the three top defects ([`rag_evaluation.md`](rag_evaluation.md))

**Phase 1 — Measurement** · *blocks everything below*

- [ ] Labeled corpus: 30–50 real policies, paragraph-level `rule_id` labels
- [ ] Retrieval metrics (recall@k, MRR) measured independently of the LLM
- [ ] End-to-end precision/recall with false positives on benign text tracked separately
- [ ] pytest suite + regression gate on `rules.json` and retrieval changes

**Phase 2 — Recall** · *depends on Phase 1 baseline; ship and measure as one change*

- [ ] `k=1` → `k=3` with `similarity_search_with_score()`
- [ ] Similarity threshold, so a weak match reports nothing instead of guessing
- [ ] Extend the response schema to express multiple violations per paragraph —
      *without this, raising `k` changes retrieval but not output*
- [ ] Derive the keyword pre-filter from `rules.json` instead of the hardcoded whitelist,
      and move it out of `analyse_batch`

**Phase 3 — Knowledge base** · *each change requires a vector DB rebuild + Phase 1 regression run*

- [ ] Widen the 4 narrow `semantic_description` fields flagged in the audit
- [ ] Add GDPR Art. 6(1)(f) legitimate interests — the most commonly abused basis, currently uncovered
- [ ] Build-time check that the committed index matches `rules.json`

**Phase 4 — Trust & product** · *gated on Phase 1 numbers being good enough to stand behind*

- [ ] Pre-scan data-handling disclosure naming the processor
- [ ] Confidence signalling in the UI — say when a clean scan is low-confidence
- [ ] PDF and URL input; lift the 15-paragraph cap
- [ ] Vendor background check, against the three criteria in [Project Structure](#project-structure)

**Explicitly out of scope for now** — non-EU/Swiss regulations (CCPA, PIPEDA, UK GDPR),
multi-model consensus, and self-hosted inference. All defensible, none affordable at
current scope; the data-handling risk is the one that would force self-hosting sooner.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contact

Alison Meng — alisonmeng2015@gmail.com

Project Link: [https://github.com/alisonmeng/compliance-scanner](https://github.com/alisonmeng/compliance-scanner)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Acknowledgments

* [GDPR-Info](https://gdpr-info.eu) — full GDPR text and article references
* [Swiss FDPIC](https://www.edoeb.admin.ch) — nFADP guidance
* [EU AI Act Explorer](https://artificialintelligenceact.eu) — AI Act article text
* [CNIL](https://www.cnil.fr/en) — risk-severity methodology
* [LangChain](https://python.langchain.com) · [ChromaDB](https://www.trychroma.com) · [Streamlit](https://streamlit.io)
* [Best-README-Template](https://github.com/othneildrew/Best-README-Template) — README structure

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/alisonmeng/compliance-scanner.svg?style=for-the-badge
[contributors-url]: https://github.com/alisonmeng/compliance-scanner/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/alisonmeng/compliance-scanner.svg?style=for-the-badge
[forks-url]: https://github.com/alisonmeng/compliance-scanner/network/members
[stars-shield]: https://img.shields.io/github/stars/alisonmeng/compliance-scanner.svg?style=for-the-badge
[stars-url]: https://github.com/alisonmeng/compliance-scanner/stargazers
[issues-shield]: https://img.shields.io/github/issues/alisonmeng/compliance-scanner.svg?style=for-the-badge
[issues-url]: https://github.com/alisonmeng/compliance-scanner/issues
[license-shield]: https://img.shields.io/github/license/alisonmeng/compliance-scanner.svg?style=for-the-badge
[license-url]: https://github.com/alisonmeng/compliance-scanner/blob/main/LICENSE
[Python-badge]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[Streamlit-badge]: https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white
[Streamlit-url]: https://streamlit.io/
[LangChain-badge]: https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white
[LangChain-url]: https://python.langchain.com/
[Gemini-badge]: https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white
[Gemini-url]: https://ai.google.dev/
[Chroma-badge]: https://img.shields.io/badge/ChromaDB-FF6B6B?style=for-the-badge&logo=databricks&logoColor=white
[Chroma-url]: https://www.trychroma.com/
