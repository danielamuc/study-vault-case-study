---
type: project
id: compliance-rag
title: Compliance RAG
part_of:
- '[[fdd26-w5-rag]]'
team: Group 2
date: 2026-08
status: done
applies:
- '[[retrieval-augmented-generation]]'
- '[[rag-ingestion]]'
- '[[sliding-window-chunking]]'
- '[[embedding]]'
- '[[cosine-similarity]]'
- '[[dense-retrieval]]'
- '[[bm25]]'
- '[[metadata-filtering]]'
- '[[hybrid-search]]'
- '[[reciprocal-rank-fusion]]'
- '[[over-retrieval]]'
- '[[top-k-retrieval]]'
- '[[grounded-generation]]'
- '[[abstention]]'
- '[[retrieval-evaluation]]'
- '[[gold-set]]'
- '[[recall-at-k]]'
- '[[context-window]]'
- '[[python]]'
- '[[rank-bm25]]'
- '[[qdrant]]'
- '[[openrouter]]'
- '[[google-colab]]'
- '[[embedding-model]]'
sources:
- ETH_PROJECTS/RAG Summer Workshop/Final project (summit it)/Daniela_compliance_rag_project.ipynb
- ETH_PROJECTS/RAG Summer Workshop/Final project (summit it)/compliance_rag_submission/solutions/part1_ingestion.py
- ETH_PROJECTS/RAG Summer Workshop/Final project (summit it)/compliance_rag_submission/solutions/part2_retrieval.py
- ETH_PROJECTS/RAG Summer Workshop/Final project (summit it)/compliance_rag_submission/SUBMISSION.md
- ETH_PROJECTS/RAG Summer Workshop/Final project (summit it)/Group 2_compliance_rag_submission.zip
- ETH_PROJECTS/RAG Summer Workshop/FDD-WE5-public/project/README.md
---
# Compliance RAG

**What it was:** the final project of Weekend 5. A question-answering system for employees: they ask about company policy and get an answer grounded in the policy text, with sources. The data is 9 synthetic policy documents (code of conduct, information security, leave, procurement, expenses, performance review, AI usage, data retention, remote work). A course gold set of 12 questions (6 lexical, 6 semantic) measures the retrieval.

**What I built:** the 8 core functions of the RAG pipeline. All 8 test cells pass (32 checks).
- `sliding_window`: word-level chunking with overlap; rejects an overlap equal to or larger than the chunk size.
- `ingest_document`: load, chunk, embed in one batch call, store in Qdrant; copies the document metadata onto every chunk.
- `apply_metadata_filter`: keeps only chunks whose metadata matches every filter key.
- `cosine_similarity`: vectorised similarity of the query against all chunk vectors, with a divide-by-zero guard.
- `keyword_search`: BM25 over the filtered candidates (rank_bm25).
- `reciprocal_rank_fusion`: fuses ranked lists by rank only, 1/(k + rank) with k = 60.
- `hybrid_search`: over-retrieval in both branches, then RRF, then cut to top-k.
- `retrieve_and_answer`: retrieves, abstains without calling the LLM when nothing is found, otherwise answers from the retrieved context.

**What I measured:** most experiment cells are course-provided and ran on my functions. The K = 10 sweep is my own added experiment.
- Retriever comparison, document recall@3: BM25 0.75, embedding 0.58, hybrid 0.83 (offline stand-in embedder).
- Overlap 0 to 40 words raised answer recall from 0.42 to 0.58 at about 4% more context.
- Chunk size: no chunking gives the best answer recall but about 9 times the context of 120-word chunks.
- K from 3 to 10 (my experiment): better recall, about three times the context.
- With a real embedding model, hybrid answer recall rose from 0.42 to 0.92, the best of the three retrievers. Fusion inherits the quality of its inputs.
- Abstention by score threshold is fragile: an off-topic question (the unladen swallow) scored 7.55 with BM25, above the 3.0 threshold, because it shares stopwords with every chunk.

**What I concluded:**
- Overlap buys answer recall at almost no context cost.
- Larger K and larger chunks trade context cost for recall. In my words: "there is no one single winning strategy; it is a business decision".
- RRF fuses ranks, not scores, so a chunk found by both retrievers wins. I checked this with a worked example at k = 60.
- I explained HNSW in my own words in the notebook: a layered graph, long links on top, all vectors at the bottom.

**Open points:** the submission is named "Group 2"; the split of work within the group is not documented. Grade and feedback are not in the files.

<!-- generated:start (written by tools/vault.py build, do not edit) -->
**Applies:**
- *concept*: [[context-window|Context window]], [[embedding-model|Embedding model]], [[embedding|Embedding]], [[gold-set|Gold set]], [[retrieval-evaluation|Retrieval evaluation]], [[top-k-retrieval|Top-k retrieval]]
- *method*: [[abstention|Abstention]], [[bm25|BM25]], [[dense-retrieval|Dense retrieval]], [[grounded-generation|Grounded generation]], [[hybrid-search|Hybrid search]], [[metadata-filtering|Metadata filtering]], [[over-retrieval|Over-retrieval]], [[rag-ingestion|RAG ingestion pipeline]], [[reciprocal-rank-fusion|Reciprocal rank fusion]], [[retrieval-augmented-generation|Retrieval-augmented generation]], [[sliding-window-chunking|Sliding-window chunking]]
- *metric*: [[cosine-similarity|Cosine similarity]], [[recall-at-k|Recall@k]]
- *tool*: [[google-colab|Google Colab]], [[openrouter|OpenRouter]], [[python|Python]], [[qdrant|Qdrant]], [[rank-bm25|rank_bm25]]
**Wider areas (inferred):** [[artificial-intelligence|Artificial intelligence]], [[chunking|Chunking]], [[classification|Classification]], [[classification-metrics|Classification metrics (accuracy, balanced accuracy, F1)]], [[computer-science|Computer science]], [[data-management|Data management]], [[deep-learning|Deep learning]], [[ai-evaluation|Evaluation of AI systems]], [[information-retrieval|Information retrieval]], [[large-language-model|Large language model]], [[lexical-retrieval|Lexical retrieval]], [[machine-learning|Machine learning]], [[mathematics|Mathematics]], [[natural-language-processing|Natural language processing]], [[programming|Programming]], [[rag-evaluation|RAG evaluation]], [[rank-fusion|Rank fusion]], [[recall|Recall]], [[software-engineering|Software engineering]], [[supervised-learning|Supervised learning framework (model, loss, optimisation)]], [[vector-database|Vector database]], [[vector-similarity|Vector similarity]]
**Part of:** [[fdd26-w5-rag|Weekend 5: Retrieval-augmented generation]], [[fdd26-summer-workshop|Summer Workshop 2026: From Data to Solutions]], [[mas-applied-information-data-science|MAS Applied Information and Data Science]]

**Where to find more:** (local file links removed in this public copy)
<!-- generated:end -->
