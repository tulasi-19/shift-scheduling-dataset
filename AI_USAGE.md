# AI usage disclosure

**Tool used:** Claude (Anthropic) in a chat session, for the whole project. Prompts are in [`PROMPT_HISTORY.md`](PROMPT_HISTORY.md).

## Where AI accelerated my work
* Turned the problem statement into a design: entity list, ID formats, business rules (R1-R8), the five injected edge cases.
* Wrote the first versions of `generate_data.py` (generator, data dictionary, SQL/JSON/CSV export), `validate_data.py`,
  `reproducibility_check.py`, the README and the requirements checklist spreadsheet.
* Ran the code in its own sandbox, debugged it, and tested extra seeds (6 full-scale, 12 small).
* Explained how to run the project, use VS Code and push to GitHub.

## Where I relied on AI heavily
* Almost all of the code and the data-model design were written by the AI; I did not write the generator or validator line by line.
* The scheduling approach (greedy, skills first, lowest utilisation first), the swap model (one-way covers) and the interpretation of
  the `SHIFT-` ID as a slot ID were AI proposals that I accepted. They are listed as trade-offs in the README.

## What I personally reviewed, changed and validated
* I ran the generator, the validator and the reproducibility check on my own Windows machine (Python 3.10.11) and checked the output
  (195/195 checks, `PASS`, row counts 2,000 employees / 100 teams / 5,000 leave requests).
* I ran extra tests myself: a different seed (`--seed 1`) and a deliberately corrupted copy of the data.
  The seed-1 run **found a real bug** (injected swap events could have a timestamp order that broke the history). I reported it,
  the generator was fixed, and the checks were re-run on many seeds.
* The corrupted-data test showed the validator fails when data is wrong (4 checks failed), so the checks are not just printing "pass".
* I asked for a requirements-vs-delivery check, which showed weak spots (two always-pass validator checks, no independent
  check of swap decisions). I asked for them to be fixed; they were replaced by real checks.
* I read `README.md` and `generate_data.py` and can explain the five injected problems.
* I can explain why the data is reproducible (fixed seed and a separate random stream for each generation phase).
* I created the GitHub repository and pushed the code, README and the starter dataset.

## Limitations of AI use I am aware of
* The generator and validator were written by the same AI, so shared misunderstandings are possible. I reduced this by testing across
  many seeds, a corrupted-data test, and a reproducibility check, but I did not write an independent implementation by hand.
* The holiday calendar is illustrative and was not verified against an official source.

## Development timeline (honest note)
The code was developed and tested in one chat session, then run locally and committed to GitHub. The first commit therefore contains
the generator, validator and starter dataset together; later commits add documentation, design notes and this AI disclosure.
Commit timestamps are real and have not been edited.