"""Day 2 3세션 · 고르기 — 임베딩 · 청킹 · 색인 · 검색 · 주입 · 호출.

    from src import rag
    chunks = rag.chunk_folder("data/kb")
    idx = rag.Index.build(chunks)
    answer, hits = rag.ask("연차는 며칠 전에 신청하나요?", idx)

임베딩 모델
- 기본: 한국어 특화 공개 모델(jhgan/ko-sroberta-multitask) — 다국어 모델보다 한국어 문장 유사도를 더 정확히 잰다 (처음 실행 때 약 420MB를 내려받는다 — 강의 전날 미리)
- EMBED=hash: 내려받기 없이 글자 조각으로 만드는 간이 벡터. 인터넷이 막힌 강의장 · 리허설용.
  뜻을 이해하지 못하므로 "단어를 바꿔 쓴 질문"에서 성능이 떨어진다 — 그것도 관찰 거리다.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from common import llm

ROOT = Path(__file__).resolve().parents[1]
ST_MODEL = os.getenv("ST_MODEL", "jhgan/ko-sroberta-multitask")
EMBED = os.getenv("EMBED", "st")          # st | hash


# ================================================================ 임베딩
class HashEmbedder:
    """글자 2·3-gram을 해시해 만든 간이 벡터 (오프라인 대비용)."""
    name = "hash-char-ngram"

    def __init__(self, dim: int = 2048):
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        t = re.sub(r"\s+", " ", text.lower())
        for n in (2, 3):
            for i in range(len(t) - n + 1):
                g = t[i:i + n]
                if g.strip():
                    h = int(hashlib.md5(g.encode()).hexdigest()[:8], 16)
                    v[h % self.dim] += 1.0
        return v

    def encode(self, texts, normalize_embeddings: bool = True, **_):
        single = isinstance(texts, str)
        arr = np.stack([self._vec(t) for t in ([texts] if single else texts)])
        if normalize_embeddings:
            arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
        return arr[0] if single else arr


_embedder = None


def embedder():
    """문서와 질문을 반드시 같은 모델로 바꾼다 — 그래서 한 번만 만들어 함께 쓴다."""
    global _embedder
    if _embedder is None:
        if EMBED == "hash":
            _embedder = HashEmbedder()
        else:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer(ST_MODEL)
            _embedder.name = ST_MODEL
    return _embedder


def embed(texts):
    """정규화된 벡터 — 내적이 곧 코사인 유사도."""
    return embedder().encode(texts, normalize_embeddings=True)


# ================================================================ 청킹
HEADING = r"\n(?=#|제\d+조|■|Q\.)"     # 제목 · 조항 · 항목 · FAQ 질문 앞에서 자른다


def chunk(text: str, source: str, max_len: int = 800, overlap: int = 100,
          pattern: str | None = HEADING) -> list[dict]:
    """구조를 따라 먼저 자르고, max_len보다 긴 조각만 다시 나눈다.

    pattern=None 이면 구조를 무시하고 글자 수로만 자른다 (고장 내기 실습용).
    """
    doc_title = text.strip().split("\n")[0].lstrip("# ").strip()
    parts = re.split(pattern, text) if pattern else [text]
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        head = p.split("\n")[0][:40]
        step = max(1, max_len - overlap)
        for i in range(0, len(p), step):
            piece = p[i:i + max_len]
            out.append({"text": piece, "source": source, "doc_title": doc_title, "title": head})
            if i + max_len >= len(p):
                break
    # 아주 짧은 조각(제목 한 줄 등)은 다음 조각에 붙인다
    merged = []
    for c in out:
        if merged and len(merged[-1]["text"]) < 40 and merged[-1]["source"] == c["source"]:
            c = {**c, "text": merged[-1]["text"] + "\n" + c["text"], "title": merged[-1]["title"]}
            merged[-1] = c
        else:
            merged.append(c)
    return merged


def load_folder(folder: str | Path = "data/kb") -> list[tuple[str, str]]:
    folder = Path(folder)
    if not folder.is_absolute():
        folder = ROOT / folder
    return [(p.name, p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.txt"))]


def chunk_folder(folder="data/kb", **kw) -> list[dict]:
    out = []
    for name, text in load_folder(folder):
        out.extend(chunk(text, name, **kw))
    for i, c in enumerate(out):
        c["id"] = f"c{i:04d}"
    return out


# ================================================================ 키워드 검색 (BM25)
def _terms(text: str) -> list[str]:
    """단어 + 한글 글자 2-gram. 조사가 붙어도 걸리게 한다."""
    t = text.lower()
    words = re.findall(r"[a-z0-9][a-z0-9\-\.]*|[가-힣]+", t)
    grams = []
    for w in words:
        if re.match(r"[가-힣]", w):
            grams += [w[i:i + 2] for i in range(len(w) - 1)] or [w]
        else:
            grams.append(w)
    return grams


class Keyword:
    """가장 단순한 BM25. 코드 · 번호 · 정확한 고유명사에 강하다."""

    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.docs = [Counter(_terms(c["text"])) for c in chunks]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / max(len(self.lens), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def search(self, q: str, k: int = 3) -> list["Hit"]:
        qt = _terms(q)
        scores = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in qt:
                if t in d:
                    f = d[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
            scores.append(s)
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [Hit(self.chunks[i]["text"], self.chunks[i]["source"], self.chunks[i]["title"], scores[i], "score")
                for i in order]


# ================================================================ 벡터 색인 (chroma)
@dataclass
class Hit:
    text: str
    source: str
    title: str
    value: float            # 의미 검색은 거리(작을수록 가깝다), 키워드는 점수(클수록 가깝다)
    kind: str = "distance"

    def __str__(self):
        return f"{self.value:.3f}  {self.source:<24} {self.text[:50].replace(chr(10), ' ')}"


class Index:
    """벡터 DB가 하는 일 — 저장 · 근접 검색 · 메타데이터 필터."""

    def __init__(self, col, chunks):
        self.col, self.chunks = col, chunks

    @classmethod
    def build(cls, chunks: list[dict], name: str = "kb", persist: str | None = None) -> "Index":
        import chromadb
        client = chromadb.PersistentClient(path=str(ROOT / persist)) if persist else chromadb.EphemeralClient()
        name = f"{name}-col"
        try:
            client.delete_collection(name)
        except Exception:
            pass
        col = client.create_collection(name, embedding_function=None, metadata={"hnsw:space": "cosine"})
        texts = [c["text"] for c in chunks]
        col.add(ids=[c.get("id", f"c{i:04d}") for i, c in enumerate(chunks)],
                documents=texts,
                embeddings=embed(texts).tolist(),
                metadatas=[{"파일": c["source"], "제목": c["title"], "문서": c["doc_title"]} for c in chunks])
        return cls(col, chunks)

    def search(self, q: str, k: int = 3, where: dict | None = None) -> list[Hit]:
        hits = self.col.query(query_embeddings=[embed(q).tolist()], n_results=k, where=where,
                              include=["documents", "distances", "metadatas"])
        return [Hit(d, m["파일"], m["제목"], dist) for d, dist, m in
                zip(hits["documents"][0], hits["distances"][0], hits["metadatas"][0])]


# ================================================================ 주입 · 호출
RULES = """<규칙>
- 아래 <자료>에 있는 내용만으로 답하라.
- 문장마다 근거 자료 번호를 [1]처럼 붙여라.
- 자료에 답이 없으면 "자료에 없음"이라고만 답하라.
</규칙>"""

RULES_NO_REFUSAL = """<규칙>
- 아래 <자료>를 참고해 답하라.
- 문장마다 근거 자료 번호를 [1]처럼 붙여라.
</규칙>"""

LAST_PROMPT = ""


def make_prompt(q: str, hits: list[Hit], rules: str = RULES) -> str:
    """규칙은 앞, 자료는 번호와 출처를 달아 가운데, 질문은 맨 끝."""
    blocks = "\n".join(f'<자료 번호="{i + 1}" 출처="{h.source} · {h.title}">\n{h.text}\n</자료>'
                       for i, h in enumerate(hits))
    return f"{rules}\n\n{blocks}\n\n<질문>{q}</질문>"


def ask(q: str, idx: Index, k: int = 3, *, rules: str = RULES, model: str | None = None,
        drop_context: bool = False, max_tokens: int = 600):
    """검색 → 주입 → 호출. (답, 넣은 자료 목록)을 돌려준다.

    drop_context=True 는 '자료를 프롬프트에서 빼먹는 버그' — 고장 내기 실습용.
    """
    global LAST_PROMPT
    hits = idx.search(q, k)
    LAST_PROMPT = make_prompt(q, [] if drop_context else hits, rules)
    r = llm.call(LAST_PROMPT, model=model, max_tokens=max_tokens)
    return r.text, hits


def cited(answer: str) -> list[int]:
    """답에 붙은 각주 번호 [n]."""
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})


def debug(q: str, idx: Index, k: int = 3, **kw):
    """답만 보지 말고 중간을 찍는다 — 1·2단계(검색 · 청크), 3단계(최종 프롬프트), 4단계(답)."""
    print("---- 검색 결과 (거리 · 작을수록 가깝다) ----")
    for h in idx.search(q, k):
        print(h)
    answer, hits = ask(q, idx, k, **kw)
    print("---- 최종 프롬프트 ----")
    print(LAST_PROMPT)
    print("---- 답 ----")
    print(answer)
    return answer, hits
