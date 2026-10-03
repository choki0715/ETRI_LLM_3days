"""임베딩 모델을 미리 내려받는다 — 강의 전날 한 번.   python tools/download_model.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import rag  # noqa: E402

if rag.EMBED == "hash":
    print("EMBED=hash 입니다. 내려받을 것이 없습니다.")
else:
    v = rag.embed(["연차는 사용 3일 전까지 신청한다", "휴가 신청은 어떻게 해요?"])
    print("내려받기 완료:", rag.ST_MODEL, "· 벡터 크기", v.shape[1], "· 유사도", round(float(v[0] @ v[1]), 3))
