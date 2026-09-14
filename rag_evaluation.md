# Compliance Scanner RAG Tool — Evaluation Notes

## Architecture Summary

```
User text → chunk by \n\n → keyword filter → ChromaDB similarity_search(k=1)
  → matched rule → [chunk + rule] → Gemini LLM → structured violation result
```

- **23 rules** embedded via `semantic_description` field (ChromaDB / gemini-embedding-001)
- LLM evaluates each chunk against **only the single top-matched rule**
- Vendor background check is a completely separate DuckDuckGo web search (not RAG)
- Batch size: 5 chunks / batch, max 15 chunks per scan

---

## What's Working Well

| Area | Notes |
|------|-------|
| Module separation | `analyser`, `news_agent`, `vector_store`, `ui` are clean |
| Pydantic structured output | Prevents hallucinated JSON, enforces schema |
| Rate limit error handling | Graceful 429 handling + batch skipping |
| Rule quality | Exception-aware, comprehensive_clause is rich legal text |
| Two-field design | Embedding `semantic_description` + sending `comprehensive_clause` to LLM is smart |

---

## Key Issues Found

### 1. k=1 Kills Multi-Rule Detection (Critical)
**File:** `core/analyser.py:60`

Each chunk is evaluated against exactly 1 rule. A clause that violates data retention, international transfer, AND purpose limitation only gets reported as 1 violation. Estimated 40–60% of multi-violation clauses are under-reported.

**Fix direction:** Change `k=1` → `k=3`, use `similarity_search_with_score()`, filter by threshold.

---

### 2. Keyword Filter Has Large Blind Spots (High)
**File:** `core/analyser.py:55–56`

The 15-word whitelist silently skips clauses for 7 of 23 rules. Missing terms:

| Missing keyword | Rule being skipped |
|----------------|-------------------|
| `information`, `personal details` | Paraphrased data clauses |
| `fingerprint`, `pixel`, `beacon` | ePrivacy / cookies |
| `arbitration`, `dispute` | UCTD forced arbitration |
| `children`, `minors`, `age` | GDPR Art. 8 (children) |
| `terminate`, `suspend`, `ban` | DSA account termination |
| `subscription`, `cancel` | CRD subscription traps |
| `algorithm`, `automated`, `profiling` | GDPR automated decisions |

---

### 3. No Similarity Score Threshold (Medium)
**File:** `core/analyser.py:60–62`

`similarity_search(k=1)` always returns a result even if similarity is 0.1. Wastes LLM calls and risks false positives on generic clauses that passed the keyword filter.

---

### 4. Some Semantic Descriptions Are Narrow (Medium)
**File:** `data/rules.json`

Rules whose `semantic_description` could be widened to improve retrieval:

| Rule ID | Problem | Example missed clause |
|---------|---------|----------------------|
| `GDPR_ART21_OBJECTION` | Only mentions "emails, newsletters" | "commercial communications", "product updates" |
| `GDPR_ART22_AUTOMATED` | Focused on hiring/loans/housing | "decisions affecting your account" |
| `UCTD_ART03_ARBITRATE` | Mentions "Dispute Resolution section" label | Clauses without that label |
| `EUAI_ART50_TRANSPARENCY` | Very short description | "our assistant", "our smart features" |

---

### 5. Rule Coverage Gaps (Low — Fine for v1)
- No **GDPR Art. 6(1)(f) legitimate interests** — very commonly abused phrase
- No **GDPR data protection by design**
- No **PIPEDA/CCPA** if targeting non-EU users
- No **UK PECR** for post-Brexit UK users

---

## Code Structure Assessment

| Area | Status |
|------|--------|
| Module separation | ✅ Clean |
| Pydantic output | ✅ Good |
| Error handling | ✅ Good |
| Keyword filter (hardcoded inline) | ⚠️ Should be in config/separate module |
| Scan limit hardcoded as `3` in UI | ⚠️ Should be a named constant |
| No test suite | ⚠️ `__main__` block exists but no pytest |
| News agent decoupled from RAG | ⚠️ Design consideration |
| No similarity threshold | ❌ Any k=1 result is used regardless of relevance |

---

## Recommended Fix Priority

| Priority | Change | Files | Impact |
|----------|--------|-------|--------|
| 1 | `k=1` → `k=3` + similarity threshold | `core/analyser.py` | Catches multi-rule violations |
| 2 | Expand keyword filter | `core/analyser.py` | Stops missing 7 rule categories |
| 3 | Widen 4 narrow semantic_descriptions | `data/rules.json` + rebuild vector DB | Better retrieval precision |
| 4 | Add legitimate-interests rule | `data/rules.json` | Covers most-abused GDPR phrase |

---

## Verdict

**The rules.json is solid — don't start there.** The bottleneck is the retrieval logic (`k=1` + weak keyword filter). Fix those first and you'll get significantly better coverage with zero data changes. Then tune semantic_descriptions for the 4 narrow rules.

The code structure is clean enough for a v1. The main structural debt is the hardcoded keyword filter that needs to move out of `analyse_batch`.
