# Live handbook answerer

This project retrieves three current public [GitLab People handbook](https://handbook.gitlab.com/handbook/people-group/) pages and answers a People Operations question with the locally installed Qwen model through Ollama. It uses live source pages each run. There are no invented policies, employee records, or simulated HRIS actions.

## Run

Install [Ollama](https://ollama.com/) and a model, then run with Python 3.11 or newer:

```bash
ollama pull qwen3:8b
python handbook_answerer.py "How should a team member request paid time off?"
```

The output contains the answer, quoted source passages, URLs, and an `abstained` flag. Network access is required. The tool exits with an error if the live handbook cannot be read or the model is unavailable.

## Why this is relevant

The [Deepgram People AI & Automation Engineer position](https://jobs.ashbyhq.com/deepgram/bf8ea79f-f380-467e-8349-ea1ea8281316) involves giving employees useful answers from current People information. This project demonstrates live retrieval, local model use, citations, and explicit abstention. It does not access private People systems or perform employee actions. A production deployment would need source permissions, human review for sensitive answers, identity, evaluation on real employee questions, and monitoring.

## Design

1. Fetch public handbook pages over HTTPS on every run.
2. Extract the page's main content and rank passages against the question.
3. Provide the three strongest passages to the local model.
4. Return the answer only with a visible citation and the source text for review.

Model text is fallible. Citations identify the material supplied to the model; they do not independently prove every sentence in its answer.
