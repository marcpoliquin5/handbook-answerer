# Live handbook answerer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Dependencies: standard library only](https://img.shields.io/badge/dependencies-stdlib_only-brightgreen.svg)

This project retrieves three current public [GitLab People handbook](https://handbook.gitlab.com/handbook/people-group/) pages and answers a People Operations question with the locally installed Qwen model through Ollama. It uses live source pages each run. There are no invented policies, employee records, or simulated HRIS actions.

## Run

Install [Ollama](https://ollama.com/) and a model, then run with Python 3.11 or newer. The script uses only the Python standard library, so there is nothing to `pip install`:

```bash
ollama pull qwen3:8b
python handbook_answerer.py "How should a team member request paid time off?"
```

The output contains the answer, quoted source passages, URLs, and an `abstained` flag. Network access is required. The tool exits with an error if the live handbook cannot be read or the model is unavailable.

## Use cases

- **Employee self-service.** Answer common People Operations questions (time off, onboarding, policies) from the current handbook instead of a stale FAQ.
- **Grounded answers with abstention.** Every answer must cite a supplied passage; if the model gives no verifiable citation, the tool abstains and returns the sources for human review.
- **Private, local inference.** The model runs on your machine through Ollama, so questions are not sent to a hosted model API.
- **A reference pattern.** A small, readable example of retrieval-augmented generation (RAG) with live sources, citations, and explicit failure modes.

## Why it matters

People teams need employees to get accurate answers from current policy, not confident guesses. This project demonstrates live retrieval, local model use, citations, and explicit abstention. It does not access private People systems or perform employee actions. A production deployment would need source permissions, human review for sensitive answers, identity, evaluation on real employee questions, and monitoring.

## Design

1. Fetch public handbook pages over HTTPS on every run.
2. Extract the page's main content and rank passages against the question.
3. Provide the three strongest passages to the local model.
4. Return the answer only with a visible citation and the source text for review.

Model text is fallible. Citations identify the material supplied to the model; they do not independently prove every sentence in its answer.

## Sample retrieval output

The retrieval step can be run on its own, without a model. This is real output from the live handbook on 2026-10-17 for the question *"How should a team member request paid time off?"* (passages truncated):

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

Produced with:

```bash
python -c "
import handbook_answerer as h
q = 'How should a team member request paid time off?'
pages = {t: h.fetch_page(u) for t, u in h.PAGES.items()}
for i, s in enumerate(h.retrieve(q, pages), 1):
    print(i, s['title'], s['score'], s['url']); print('   ', s['text'][:300])
"
```

The full command (`python handbook_answerer.py "..."`) sends these passages to the local model and prints JSON with `answer`, `sources`, and `abstained` fields. Handbook content changes over time, so passages and scores will differ on later runs.

## License

[MIT](LICENSE)
