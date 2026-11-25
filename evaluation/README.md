# Evaluation: LLM-as-judge

Can an AI agent answer questions about my studies correctly, using only the vault?

## Method

1. **Test set:** 50 questions of several types: lookups (16), project facts (10), taught or applied (5),
   inference over links (5), concept questions (5), trap questions (5), multi-hop (3) and one
   abstention question. The gold answers come from the **raw sources** (slides, my notebooks,
   screenshots), not from the cards, so the test does not check the vault against itself.
2. **Two consumers:**
   - *vault mode:* the agent may read only the cards, the index and the catalog (the Claude Code case);
   - *export mode:* the agent may read only the one-file export (the claude.ai Project case).
3. **Two judges:** Claude Sonnet and Claude Opus score every answer independently:
   2 = correct and complete, 1 = partly correct, 0 = wrong, invented or missing. A false claim about me
   (for example, that I applied something I only heard in a lecture) scores 0.
4. **Measures:** [score.py](score.py) computes the totals per judge and mode, the agreement between the
   judges (Cohen's kappa) and the retrieval hit rate (did the agent open at least one of the cards
   the question needs?).

## Results

| Run | Vault mode | Export mode | Notes |
| --- | --- | --- | --- |
| 1 | 89% / 92% (Opus / Sonnet), kappa 0.73 | 72% / 75%, kappa 0.89 | First course. Retrieval hit rate 18/18, 2.9 files per question |
| 2 | 6/6 on the re-asked questions | 14/14 on the re-asked questions | After the fixes from run 1 |
| 3 | 100% / 100% on 28 questions | 98% / 98% | After a second course |
| 4 | 91% / 96% on 28 questions, kappa 0.38 | 88% / 89% (compact export), kappa 0.66 | Five more courses. Retrieval hit rate 28/28, 2.1 files per question |
| 5 | 4/4 | 4/4 | Re-ask after fixing four cards that were too thin |

## What the runs found and fixed

- **Missing facts in cards.** A card on Graph RAG lacked the course's criteria for when a graph is not
  worth it; a card on training compute did not say where the factor 6 comes from. Added.
- **Missing facts in the export.** No sources, then no lecturer names. The build now writes them.
- **A wrong gold answer.** In run 4 the Opus judge opened my notebook and found that a different model
  had won than my gold answer said. Both agents had answered correctly from the vault. Gold corrected.
- **Compact export trade-off.** The compact export (about 55k tokens instead of 150k) has no page
  numbers, so a question asking for pages loses a point there. The full export keeps them.
- **Low kappa with high scores.** In run 4 the judges agreed exactly on 25 of 28 vault answers, but kappa
  is only 0.38 because almost every score is 2, so each disagreement weighs heavily.

## Sample questions

The full question set stays private, because the gold answers contain course content. These five are
about my own work:

| Type | Question | Gold answer |
| --- | --- | --- |
| Taught or applied | Has Daniela applied reranking, for example a cross-encoder, in a project? | No. Reranking was taught in Weekend 5, but her Compliance RAG project uses hybrid search with reciprocal rank fusion and no reranker. |
| Project | Which fusion method did Daniela implement in Compliance RAG, and with which constant? | Reciprocal rank fusion, 1/(k + rank) per list, with k = 60. |
| Project | In AI in Industry Project 3, how did her POMO model compare with OR-Tools on the 60-customer instance (seed 99)? | Cost 27.46 against 27.88, 1.54% better; both used 7 routes. |
| Project | In the Bellman equations exercise, how many sweeps did value iteration need, and what was V* of the start state? | 7 sweeps; V*(0,0) = 1.81. |
| Abstention | What score did her two LLM judges give her skill in Innovation with GenAI Exercise 6? | Not recorded. The answer must say it is not known. |
