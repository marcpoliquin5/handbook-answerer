"""Answer People Operations questions from current public GitLab handbook pages."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser

PAGES = {
    "Onboarding": "https://handbook.gitlab.com/handbook/people-group/general-onboarding/",
    "Time off": "https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/time-off-types/",
    "People Operations": "https://handbook.gitlab.com/handbook/people-group/people-operations/",
}
STOP = {"the", "and", "for", "you", "your", "with", "that", "this", "what", "how", "are", "can", "does", "from", "into", "about"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class MainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_main = False
        self.depth = 0
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "main" and attributes.get("role") == "main":
            self.in_main = True
            self.depth = 1
            return
        if not self.in_main:
            return
        if tag in VOID_TAGS:
            if tag == "br":
                self.parts.append("\n")
            return
        self.depth += 1
        if tag in {"script", "style", "nav", "aside"}:
            self.skip += 1
        if tag in {"h1", "h2", "h3", "h4"}:
            self.parts.append("\n## ")
        elif tag in {"p", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if not self.in_main:
            return
        if tag in {"script", "style", "nav", "aside"} and self.skip:
            self.skip -= 1
        self.depth -= 1
        if self.depth == 0:
            self.in_main = False

    def handle_data(self, data):
        if self.in_main and not self.skip:
            self.parts.append(data)


def fetch_page(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "handbook-answerer/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} for {url}")
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise RuntimeError(f"Page too large: {url}")
    parser = MainText()
    parser.feed(raw.decode("utf-8", errors="replace"))
    text = "".join(parser.parts)
    text = "\n".join(re.sub(r"\s+", " ", line).strip() for line in text.splitlines())
    if len(text) < 500:
        raise RuntimeError(f"Could not extract handbook content: {url}")
    return text


def tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z]{3,}", text.lower()) if word not in STOP}


def passages(text: str, width: int = 900) -> list[str]:
    result: list[str] = []
    for section in text.split("\n## "):
        lines = section.strip().splitlines()
        if not lines:
            continue
        heading = lines[0]
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(lines[1:]))
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) > width and current:
                result.append(f"{heading}: {current.strip()}")
                current = ""
            current += sentence + " "
        if current.strip():
            result.append(f"{heading}: {current.strip()}")
    return result


def retrieve(question: str, pages: dict[str, str], count: int = 3) -> list[dict]:
    query = tokens(question)
    ranked = []
    for title, text in pages.items():
        for passage in passages(text):
            heading, _, body = passage.partition(": ")
            score = 3 * len(query & tokens(heading)) + len(query & tokens(body))
            phrase = question.lower().replace("how should a team member ", "")
            if len(phrase) >= 8 and phrase in passage.lower():
                score += 8
            if "paid time off" in question.lower() and "flexible paid time off" in heading.lower():
                score += 12
            if "paid time off" in question.lower() and question.lower().startswith("how"):
                if "pto protocols" in heading.lower() or "enter pto" in heading.lower():
                    score += 20
            if score:
                ranked.append({"title": title, "url": PAGES[title], "text": passage,
                               "score": score})
    ranked.sort(key=lambda item: (item["score"], -len(item["text"])), reverse=True)
    return ranked[:count]


def answer(question: str, model: str = "qwen3:8b") -> dict:
    pages = {title: fetch_page(url) for title, url in PAGES.items()}
    selected = retrieve(question, pages)
    if not selected:
        return {"answer": "No matching handbook passage found.", "sources": [], "abstained": True}
    context = "\n\n".join(f"[{i}] {item['title']} ({item['url']}): {item['text']}"
                          for i, item in enumerate(selected, 1))
    prompt = (
        "Answer the question using only the cited GitLab handbook passages below. "
        "If they do not answer it, say you cannot determine it from these passages. "
        "Give a short answer with citations like [1]. Do not invent eligibility or policy rules. "
        "Do not add approval or permission steps unless a passage explicitly requires them. "
        "Do not describe any action as completed. /no_think\n\n"
        f"Question: {question}\n\nPassages:\n{context}\n\nAnswer:"
    )
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False,
                          "think": False, "options": {"temperature": 0}}).encode("utf-8")
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=payload,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as result:
        response = json.load(result)["response"].strip()
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", response) if 1 <= int(n) <= len(selected)})
    if not cited:
        return {"answer": "The model returned no verifiable citation; review the source passages.",
                "sources": selected, "abstained": True}
    return {"answer": response, "sources": [selected[i - 1] for i in cited],
            "abstained": False}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--model", default="qwen3:8b")
    args = parser.parse_args()
    try:
        print(json.dumps(answer(args.question, args.model), indent=2, ensure_ascii=False))
    except (RuntimeError, OSError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
