---
type: concept
id: hybrid-search
title: Hybrid search
kind: method
broader:
- '[[information-retrieval]]'
requires:
- '[[dense-retrieval]]'
- '[[lexical-retrieval]]'
related:
- '[[reranking]]'
sources:
- STUDIES/1. CAS 1 ETH Data and Machine Learning & Summer Workshop/Summer Camp/Week 5 RAG/2. FDD26-W5-ANN-Hybrid-Search (1).pdf#p3-5, 21-22
- STUDIES/1. CAS 1 ETH Data and Machine Learning & Summer Workshop/Summer Camp/Week 5 RAG/5. Agentic and Graph RAG (1) with my notes.pdf#p4, 46, 49
- STUDIES/2. CAS 2 ETH Mobile and Cloud Computing/AI PM/5 AI Product Development - AI Assisted Development^J Grounding and Retrieval.pdf#p50
---
# Hybrid search

**In short:** Combining dense (vector) and sparse (keyword) retrieval, often with filters, and fusing their results into one ranking.

**In the Summer Workshop (Weekend 5):** Deck 2 pipeline: retrieval of 50 to 100 candidates from over 10^7 records, rank fusion to 30 to 50, reranking to 3 to 5, then the LLM. The three retrieval strategies are dense, sparse and filtered vector search, for the three factors semantics, keywords and constraints. Deck 5 names it as the fix for precise queries where meaning-based search is weak.

**In AI Product Development:** Dense retrieval plus BM25 fused (reciprocal rank fusion) for recall and robustness. Listed among the five RAG versions.

<!-- generated:start (written by tools/vault.py build, do not edit) -->
**Taught in:** [[ai-product-development-2026|AI Product Development]] (CAS in Cloud and Mobile Computing), [[fdd26-w5-rag|Weekend 5: Retrieval-augmented generation]] (Summer Workshop 2026: From Data to Solutions › MAS Applied Information and Data Science)
**Applied in:** [[compliance-rag|Compliance RAG]], [[policy-compliance-agent|Policy-compliance verification agent]]
**Broader chain:** [[information-retrieval|Information retrieval]]
**Narrower:** [[over-retrieval|Over-retrieval]], [[rank-fusion|Rank fusion]]
**All prerequisites:** [[dense-retrieval|Dense retrieval]], [[lexical-retrieval|Lexical retrieval]], [[embedding|Embedding]], [[nearest-neighbor-search|Nearest neighbor search]], [[vector-similarity|Vector similarity]]

**Where to find more:** (local file links removed in this public copy)
<!-- generated:end -->
