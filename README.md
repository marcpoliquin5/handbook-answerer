# Handbook answerer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Dependencies: standard library only](https://img.shields.io/badge/dependencies-stdlib_only-brightgreen.svg)

Answers HR policy questions from the live [GitLab People handbook](https://handbook.gitlab.com/handbook/people-group/) with a local language model. Every answer cites the passages it used, and the tool abstains when the model cannot cite one.

A small retrieval-augmented generation (RAG) example: one 167-line Python file, no packages to install.

## How it works

1. **Fetch.** Three public handbook pages (onboarding, time off, People Operations) are downloaded over HTTPS on every run, so answers reflect the current policy text.
2. **Split.** The main content is extracted with the standard-library HTML parser and cut into passages of about 900 characters, each labelled with its section heading.
3. **Rank.** Passages are scored by keyword overlap with the question, with heading matches weighted three times as much as body matches. The top three go to the model.
4. **Answer.** A local model (default `qwen3:8b` through [Ollama](https://ollama.com/), temperature 0) is told to answer only from those passages and to cite them as `[1]`, `[2]`, `[3]`.
5. **Check.** If the reply cites none of the supplied passages, it is discarded. The tool returns `"abstained": true` and the passages for a person to review.

## Run

Requires Python 3.11 or newer, Ollama, and network access to the handbook.

```bash
ollama pull qwen3:8b
python handbook_answerer.py "How should a team member request paid time off?"
```

Output is JSON with three fields: `answer`, `sources` (title, URL, passage text and score for each cited passage) and `abstained`. Use `--model` to try a different Ollama model. The tool exits with an error if the handbook cannot be read or the model is unavailable.

## Example

Retrieval can be run without a model. This is the output from the live handbook on 2026-10-17 for *"How should a team member request paid time off?"* (rank, page, score, URL, passage; passages truncated):

```text
1 Time off 24 https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/time-off-types/
    How to Enter PTO in Workday: You can enter PTO directly into the Workday app, or through
    the Workday Slack integration. Select the day(s) you want to take > Click “Time-Off” >
    Click “Paid Time Off” > Optional: add a comment > Click “Submit” ...
2 Time off 24 https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/time-off-types/
    PTO Protocols (Planning and Coordination): Discuss planned time off with your manager first
    and provide as much notice as possible, but at least twice as many days as your planned
    time off (e.g., 6 business days notice for 3 days off). ...
3 Time off 23 https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/time-off-types/
    Flexible Paid Time Off (PTO): This page focuses specifically on GitLab’s Flexible PTO
    policy ...
```

<details>
<summary>Command that produced it</summary>

```bash
python -c "
import handbook_answerer as h
q = 'How should a team member request paid time off?'
pages = {t: h.fetch_page(u) for t, u in h.PAGES.items()}
for i, s in enumerate(h.retrieve(q, pages), 1):
    print(i, s['title'], s['score'], s['url']); print('   ', s['text'][:300])
"
```

</details>

The handbook changes over time, so passages and scores will differ on later runs.

## Design choices

- **Abstain instead of guessing.** A wrong policy answer costs more than no answer, so an uncited reply is never shown.
- **Local inference.** The question and the model's answer stay on the machine; only the public handbook pages are fetched.
- **Standard library only.** HTTP, HTML parsing and the Ollama call all use built-in modules, which keeps the whole pipeline readable in one sitting.

## Limitations

- A citation shows which passage the model pointed to. It does not prove that every sentence of the answer is supported by it.
- Ranking is keyword overlap plus a few hand-tuned boosts for paid-time-off questions. There are no embeddings, so a question phrased differently from the handbook can miss the right passage.
- The three source pages are fixed in `PAGES`.
- There is no evaluation set yet, so answer quality has not been measured.

## License

[MIT](LICENSE)
