"""
OCR 서비스 모듈
Upstage Document Digitization API로 텍스트 추출 →
ChatUpstage (Solar Pro)로 구조화 JSON 파싱
"""
import os
import json
import re
import asyncio

import requests
from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage, SystemMessage

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
UPSTAGE_OCR_URL = "https://api.upstage.ai/v1/document-digitization"

RECEIPT_PARSE_SYSTEM_PROMPT = """You are a receipt parser. Extract information from the receipt OCR text and return ONLY a valid JSON object.

Required JSON fields:
- store_name (string): store/merchant name
- receipt_date (string): date in YYYY-MM-DD format
- receipt_time (string | null): time in HH:MM format, null if not found
- category (string): one of 식료품/외식/카페/교통/의료/쇼핑/문화/기타
- items (array): list of purchased items, each with:
    name (string), quantity (number), unit_price (number), total_price (number)
- subtotal (number): subtotal amount in KRW (0 if not found)
- discount (number): discount amount in KRW (0 if none)
- tax (number): tax amount in KRW (0 if none)
- total_amount (number): final payment amount in KRW
- payment_method (string | null): payment method, null if not found

Return ONLY valid JSON. No markdown fences, no explanation."""


def _call_ocr_api(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Upstage Document Digitization API 동기 호출 → 전체 OCR 텍스트 반환"""
    if not UPSTAGE_API_KEY:
        raise ValueError("UPSTAGE_API_KEY 환경변수가 설정되지 않았습니다.")

    headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"}
    files = {"document": (filename, file_bytes, content_type)}
    data = {"model": "ocr"}

    resp = requests.post(
        UPSTAGE_OCR_URL, headers=headers, files=files, data=data, timeout=30
    )
    resp.raise_for_status()

    result = resp.json()
    # 최상위 text 필드 우선, 없으면 pages 합산
    if result.get("text"):
        return result["text"]

    pages = result.get("pages", [])
    return "\n".join(p.get("text", "") for p in pages)


def _parse_with_llm(ocr_text: str) -> dict:
    """Solar Pro LLM으로 OCR 텍스트를 구조화 JSON으로 파싱"""
    llm = ChatUpstage(api_key=UPSTAGE_API_KEY, model="solar-pro")

    messages = [
        SystemMessage(content=RECEIPT_PARSE_SYSTEM_PROMPT),
        HumanMessage(content=f"Parse this receipt OCR text into JSON:\n\n{ocr_text}"),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    # 마크다운 코드 블록 제거
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    content = content.strip()

    # JSON 객체 추출
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    return json.loads(content)


async def process_receipt(file_bytes: bytes, filename: str, content_type: str) -> dict:
    """
    영수증 파일을 OCR 처리하고 구조화 JSON 반환 (비동기 래퍼)

    1단계: Upstage Document Digitization API → OCR 텍스트
    2단계: Solar Pro LLM → 구조화 JSON
    """
    ocr_text = await asyncio.to_thread(
        _call_ocr_api, file_bytes, filename, content_type
    )

    if not ocr_text.strip():
        raise ValueError("이미지에서 텍스트를 추출할 수 없습니다.")

    parsed = await asyncio.to_thread(_parse_with_llm, ocr_text)
    return parsed
