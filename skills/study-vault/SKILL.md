---
name: study-vault
description: Daniela's Study Vault, the ontology of what she studied at ETH Zurich (programmes, courses, weekly modules, concepts, her projects, and where the files are). Use it whenever Daniela mentions her studies, ETH, a CAS or MAS course, a lecture or week, something she "learned" or "studied", her education or skills (for example for a CV, a profile, an application or an interview), or asks whether she already knows a concept such as RAG, BM25 or LLM-as-judge. Also use it before explaining an AI or data topic to her, to match what she already studied, and when she starts or designs a new project, to suggest methods she already learned that fit the project.
---

# Study Vault

The vault is at `<path to the vault>`.

1. Read `AGENTS.md` in the vault. It explains the cards, the relations and how to answer.
2. Find the card: search the card titles and aliases with grep in `concepts/`, `projects/`, `modules/` and `courses/` (for example `grep -ril "bm25" concepts projects`). Read `index.md` only for an overview question such as "what did she study?". Open at most a few cards.
3. Stay at concept level: answer from the cards only. Do not open the raw course files (slides, notebooks); for studying from the slides, the `study-companion` skill does that. Say if a concept was **taught** (a lecture covered it) or **applied** (she used it in a project). Name the card you used.
4. If the vault has no record of a topic, say so. Do not guess what she studied.
5. In a new project, look for concepts and projects in the vault that fit the problem (for example an evaluation method, a retrieval method, an earlier project with the same pattern). Propose them with the card names, so she can reuse what she learned.

Do not change the vault from another project unless Daniela asks. To change it, follow the rules in `AGENTS.md` and run `python3 tools/vault.py build`.
