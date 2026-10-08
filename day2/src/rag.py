"""Day 2 3세션 · 고르기 — 임베딩 · 청킹 · 색인 · 검색 · 주입 · 호출.

    from src import rag
    chunks = rag.chunk_folder("data/kb")
    idx = rag.Index(chunks)
    answer, hits = rag.ask("연차는 며칠 전에 신청하나요?", idx)

파일 순서
    1. 임베딩       — embed: 글을 숫자 벡터로 바꾼다
    2. 청킹         — chunk_folder: 문서를 조각으로 자른다
    3. 키워드 검색   — Keyword: 단어가 겹치는 조각을 찾는다 (BM25)
    4. 의미 검색     — Index: 벡터가 가까운 조각을 찾는다 (chroma 벡터 DB)
    5. 주입 · 호출   — make_prompt, ask: 찾은 조각을 프롬프트에 넣어 모델에게 묻는다

임베딩 모델
- 기본: 한국어 특화 공개 모델(jhgan/ko-sroberta-multitask) — 다국어 모델보다 한국어 문장 유사도를 더 정확히 잰다 (처음 실행 때 약 420MB를 내려받는다 — 강의 전날 미리)
- EMBED=hash: 내려받기 없이 글자 조각으로 만드는 간이 벡터. pytest · 강사 리허설용이며 수업에서는 쓰지 않는다.
  뜻을 이해하지 못하므로 "단어를 바꿔 쓴 질문"에서 성능이 떨어진다 — 그것도 관찰 거리다.
"""
import hashlib
import math
import os
import re
from pathlib import Path

import numpy as np

from common import llm

ROOT = Path(__file__).resolve().parents[1]                     # day2 폴더
ST_MODEL = os.getenv("ST_MODEL", "jhgan/ko-sroberta-multitask")
EMBED = os.getenv("EMBED", "st")                               # "st" = 위 모델 · "hash" = 간이 벡터


# ================================================================ 1. 임베딩
_model = None          # 임베딩 모델. 처음 쓸 때 한 번만 불러와 여기에 둔다


def get_model():
    """문서와 질문은 반드시 같은 모델로 바꿔야 한다 — 그래서 한 번만 만들어 함께 쓴다."""
    global _model
    if _model is None:
        if EMBED == "hash":
            _model = HashEmbedder()
        else:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(ST_MODEL)
    return _model


def embed(texts):
    """글을 벡터로 바꾼다. 벡터 길이를 1로 맞추므로, 두 벡터의 내적이 곧 코사인 유사도다.

    texts가 글 하나("...")면   → 벡터 하나       (모양: 차원)
    texts가 글 리스트면        → 벡터 여러 개     (모양: 글 개수 × 차원)
    """
    model = get_model()
    return model.encode(texts, normalize_embeddings=True)


class HashEmbedder:
    """글자 2·3개 묶음을 해시해 만든 간이 벡터 (pytest · 오프라인용 — 수업에서는 읽지 않아도 된다)."""

    def __init__(self, dim=2048):
        self.dim = dim

    def vector(self, text):
        v = np.zeros(self.dim, dtype=np.float32)
        t = re.sub(r"\s+", " ", text.lower())
        for n in [2, 3]:
            for i in range(len(t) - n + 1):
                piece = t[i:i + n]
                if piece.strip() == "":
                    continue
                h = int(hashlib.md5(piece.encode()).hexdigest()[:8], 16)
                v[h % self.dim] += 1.0
        return v

    def encode(self, texts, normalize_embeddings=True):
        if isinstance(texts, str):                # 글 하나면 리스트로 감싸 처리하고 첫 번째를 돌려준다
            return self.encode([texts], normalize_embeddings)[0]
        vectors = []
        for t in texts:
            vectors.append(self.vector(t))
        arr = np.array(vectors)
        if normalize_embeddings:
            arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
        return arr


# ================================================================ 2. 청킹
HEADING = r"\n(?=#|제\d+조|■|Q\.)"     # 제목(#) · 조항(제N조) · 항목(■) · FAQ 질문(Q.) 앞에서 자른다


def chunk(text, source, max_len=800, overlap=100, pattern=HEADING):
    """문서 하나를 조각 리스트로 자른다.

    1) pattern(제목 · 조항 앞)에서 먼저 자른다
    2) 그래도 max_len보다 긴 부분만 max_len 글자씩 다시 자른다 (앞 조각과 overlap 글자만큼 겹치게)
    3) 아주 짧은 조각(제목 한 줄 등)은 같은 문서의 다음 조각에 붙인다

    pattern=None 이면 구조를 무시하고 글자 수로만 자른다.
    조각 하나 = {"text": 본문, "source": 파일 이름, "doc_title": 문서 제목, "title": 조각 첫 줄}
    """
    first_line = text.strip().split("\n")[0]
    doc_title = first_line.lstrip("# ").strip()

    # 1) 구조 경계에서 자르기
    if pattern is None:
        parts = [text]
    else:
        parts = re.split(pattern, text)

    # 2) 긴 부분은 글자 수로 다시 자르기
    step = max_len - overlap            # 다음 조각이 시작하는 간격
    if step < 1:
        step = 1
    pieces = []
    for part in parts:
        part = part.strip()
        if part == "":
            continue
        title = part.split("\n")[0][:40]
        for start in range(0, len(part), step):
            pieces.append({"text": part[start:start + max_len], "source": source,
                           "doc_title": doc_title, "title": title})
            if start + max_len >= len(part):        # 끝까지 담았으면 그만 자른다
                break

    # 3) 40자 미만 조각은 같은 문서의 다음 조각 앞에 붙이기
    merged = []
    for piece in pieces:
        if len(merged) > 0:
            previous = merged[-1]
            if len(previous["text"]) < 40 and previous["source"] == piece["source"]:
                merged[-1] = {"text": previous["text"] + "\n" + piece["text"], "source": piece["source"],
                              "doc_title": piece["doc_title"], "title": previous["title"]}
                continue
        merged.append(piece)
    return merged


def load_folder(folder="data/kb"):
    """폴더의 .txt 파일을 이름 순서로 읽어 [(파일 이름, 본문), ...]으로 돌려준다."""
    folder = Path(folder)
    if not folder.is_absolute():
        folder = ROOT / folder
    files = []
    for path in sorted(folder.glob("*.txt")):
        files.append((path.name, path.read_text(encoding="utf-8")))
    return files


def chunk_folder(folder="data/kb", max_len=800, overlap=100, pattern=HEADING):
    """폴더의 모든 문서를 잘라 조각 하나의 리스트로 모은다. 조각마다 "id"(c0000, c0001, ...)를 붙인다."""
    chunks = []
    for name, text in load_folder(folder):
        for piece in chunk(text, name, max_len, overlap, pattern):
            chunks.append(piece)
    number = 0
    for c in chunks:
        c["id"] = f"c{number:04d}"
        number += 1
    return chunks


# ================================================================ 검색 결과 하나
class Hit:
    """검색 결과 조각 하나.

    value — 의미 검색이면 거리(작을수록 가깝다), 키워드 검색이면 점수(클수록 가깝다)
    """

    def __init__(self, text, source, title, value, kind="distance"):
        self.text = text
        self.source = source
        self.title = title
        self.value = value
        self.kind = kind          # "distance"(의미 검색) 또는 "score"(키워드 검색)

    def __str__(self):
        preview = self.text[:50].replace("\n", " ")
        return f"{self.value:.3f}  {self.source:<24} {preview}"


# ================================================================ 3. 키워드 검색 (BM25)
def terms(text):
    """검색용 낱말로 쪼갠다. 영어 · 숫자는 단어째, 한글은 2글자씩 (조사가 붙어도 걸리게).

    예: "AX-2041 토크는" → ["ax-2041", "토크", "크는"]
    """
    words = re.findall(r"[a-z0-9][a-z0-9\-\.]*|[가-힣]+", text.lower())
    result = []
    for w in words:
        is_korean = re.match(r"[가-힣]", w) is not None
        if is_korean and len(w) >= 2:
            for i in range(len(w) - 1):
                result.append(w[i:i + 2])
        else:
            result.append(w)
    return result


def count_terms(term_list):
    """낱말마다 몇 번 나왔는지 센다. 예: ["연차", "연차", "신청"] → {"연차": 2, "신청": 1}"""
    counts = {}
    for t in term_list:
        if t in counts:
            counts[t] += 1
        else:
            counts[t] = 1
    return counts


class Keyword:
    """가장 단순한 BM25 키워드 검색. 코드 · 번호 · 정확한 고유명사에 강하다."""

    def __init__(self, chunks, k1=1.5, b=0.75):
        self.chunks = chunks
        self.k1 = k1          # 같은 낱말이 여러 번 나올 때 점수를 얼마나 더 줄지
        self.b = b            # 긴 조각의 점수를 얼마나 깎을지

        # 조각마다 낱말 수 세기
        self.counts = []
        self.lengths = []
        for c in chunks:
            counts = count_terms(terms(c["text"]))
            self.counts.append(counts)
            self.lengths.append(sum(counts.values()))
        self.avg_length = sum(self.lengths) / max(len(self.lengths), 1)

        # 낱말마다 몇 개 조각에 나오는지 → 드문 낱말일수록 큰 가중치(idf)
        doc_freq = {}
        for counts in self.counts:
            for t in counts:
                if t in doc_freq:
                    doc_freq[t] += 1
                else:
                    doc_freq[t] = 1
        n = len(chunks)
        self.idf = {}
        for t in doc_freq:
            f = doc_freq[t]
            self.idf[t] = math.log(1 + (n - f + 0.5) / (f + 0.5))

    def search(self, q, k=3):
        """질문과 낱말이 많이 겹치는 조각 k개를 점수 높은 순서로 돌려준다."""
        query_terms = terms(q)
        scores = []
        for i in range(len(self.chunks)):
            counts = self.counts[i]
            score = 0.0
            for t in query_terms:
                if t not in counts:
                    continue
                f = counts[t]                                     # 이 조각에 그 낱말이 나온 횟수
                length_factor = 1 - self.b + self.b * self.lengths[i] / self.avg_length
                score += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * length_factor)
            scores.append(score)

        best = top_k(scores, k, largest_first=True)
        hits = []
        for i in best:
            c = self.chunks[i]
            hits.append(Hit(c["text"], c["source"], c["title"], scores[i], "score"))
        return hits


def top_k(values, k, largest_first):
    """values에서 가장 큰(또는 작은) 값 k개의 위치를 차례로 돌려준다. 같은 값이면 앞 위치가 먼저."""
    chosen = []
    for _ in range(min(k, len(values))):
        best = None
        for i in range(len(values)):
            if i in chosen:
                continue
            if best is None:
                best = i
            elif largest_first and values[i] > values[best]:
                best = i
            elif not largest_first and values[i] < values[best]:
                best = i
        chosen.append(best)
    return chosen


# ================================================================ 4. 의미 검색 (chroma 벡터 DB)
class Index:
    """벡터 DB가 하는 일 — 저장 · 근접 검색 · 메타데이터 필터.

    idx = rag.Index(chunks)          # 조각 · 벡터 · 출처를 chroma에 저장
    idx.search("질문", 3)             # 질문 벡터와 가장 가까운 조각 3개
    """

    def __init__(self, chunks, name="kb"):
        import chromadb
        client = chromadb.EphemeralClient()          # 메모리 안에만 두는 DB (파일로 저장하지 않는다)
        collection_name = name + "-col"
        try:
            client.delete_collection(collection_name)   # 같은 이름으로 전에 만든 것이 있으면 지운다
        except Exception:
            pass
        self.collection = client.create_collection(collection_name, embedding_function=None,
                                                   metadata={"hnsw:space": "cosine"})   # 거리 = 코사인 거리
        self.chunks = chunks

        ids = []
        texts = []
        metadatas = []
        number = 0
        for c in chunks:
            ids.append(c.get("id", f"c{number:04d}"))
            texts.append(c["text"])
            metadatas.append({"파일": c["source"], "제목": c["title"], "문서": c["doc_title"]})
            number += 1
        vectors = embed(texts)
        self.collection.add(ids=ids, documents=texts, embeddings=vectors.tolist(), metadatas=metadatas)

    def search(self, q, k=3, where=None):
        """질문과 가장 가까운 조각 k개를 거리 작은 순서로 돌려준다.

        where — 메타데이터 필터. 예: {"파일": "10_구매_절차.txt"} 이면 그 파일 안에서만 찾는다
        """
        q_vector = embed(q)
        result = self.collection.query(query_embeddings=[q_vector.tolist()], n_results=k, where=where,
                                       include=["documents", "distances", "metadatas"])
        texts = result["documents"][0]          # [0] = 첫 번째(유일한) 질문의 결과
        distances = result["distances"][0]
        metadatas = result["metadatas"][0]

        hits = []
        for i in range(len(texts)):
            hits.append(Hit(texts[i], metadatas[i]["파일"], metadatas[i]["제목"], distances[i]))
        return hits


# ================================================================ 5. 주입 · 호출
RULES = """<규칙>
- 아래 <자료>에 있는 내용만으로 답하라.
- 문장마다 근거 자료 번호를 [1]처럼 붙여라.
- 자료에 답이 없으면 "자료에 없음"이라고만 답하라.
</규칙>"""

LAST_PROMPT = ""       # 마지막으로 모델에 보낸 프롬프트 — 노트북에서 print(rag.LAST_PROMPT)로 본다


def make_prompt(q, hits):
    """규칙은 앞, 자료는 번호와 출처를 달아 가운데, 질문은 맨 끝."""
    blocks = []
    number = 1
    for h in hits:
        blocks.append(f'<자료 번호="{number}" 출처="{h.source} · {h.title}">\n{h.text}\n</자료>')
        number += 1
    all_blocks = "\n".join(blocks)
    return f"{RULES}\n\n{all_blocks}\n\n<질문>{q}</질문>"


def ask(q, idx, k=3, model=None, max_tokens=600):
    """검색 → 주입 → 호출. (답, 찾은 자료 목록)을 돌려준다."""
    global LAST_PROMPT
    hits = idx.search(q, k)
    LAST_PROMPT = make_prompt(q, hits)
    result = llm.call(LAST_PROMPT, model=model, max_tokens=max_tokens)
    return result.text, hits


def cited(answer):
    """답에 붙은 각주 번호 [n]을 작은 순서로, 겹치지 않게 돌려준다. 예: "… [2] … [1][2]" → [1, 2]"""
    numbers = []
    for n in re.findall(r"\[(\d+)\]", answer):
        n = int(n)
        if n not in numbers:
            numbers.append(n)
    return sorted(numbers)


def debug(q, idx, k=3):
    """답만 보지 말고 중간을 찍는다 — 검색 결과, 최종 프롬프트, 답."""
    print("---- 검색 결과 (거리 · 작을수록 가깝다) ----")
    for h in idx.search(q, k):
        print(h)
    answer, hits = ask(q, idx, k)
    print("---- 최종 프롬프트 ----")
    print(LAST_PROMPT)
    print("---- 답 ----")
    print(answer)
    return answer, hits
