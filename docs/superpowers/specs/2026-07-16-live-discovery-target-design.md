# Live Discovery Target Design

Process at most 20 ranked OpenAlex candidates and stop as soon as five usable live papers have been stored. A usable paper is either downloaded full text or a stored abstract. Candidate-level misses are logged but not shown as analysis warnings; if fewer than five are found, emit one summary warning with attempted and stored counts. Keep the existing full-text cap and abstract fallback behavior.

Configuration uses `OPENALEX_RESULT_LIMIT=20` as the candidate cap and adds `TARGET_LIVE_PAPERS=5` as the success target. No database, frontend, provider, or prompt changes are required. Per user instruction, verification is limited to formatting, backend rebuild, and container health; tests are not run.
