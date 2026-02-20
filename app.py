import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

TRANSCRIBE_MODEL = "gpt-4o-mini-transcribe"
ANALYSIS_MODEL = "gpt-4.1"


def transcribe_audio(client: OpenAI, audio_path: Path, language: str = "ko") -> str:
    with audio_path.open("rb") as audio_file:
        response = client.audio.transcriptions.create(
            model=TRANSCRIBE_MODEL,
            file=audio_file,
            language=language,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = getattr(response, "segments", None)
    if not segments:
        text = getattr(response, "text", "")
        return text.strip()

    lines: list[str] = []
    for segment in segments:
        start_sec = int(getattr(segment, "start", 0))
        mm, ss = divmod(start_sec, 60)
        speaker = "화자미상"
        text = getattr(segment, "text", "").strip()
        if text:
            lines.append(f"[{mm:02d}:{ss:02d}] {speaker}: {text}")
    return "\n".join(lines).strip()


def load_quantitative_data(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_analysis_prompt(
    transcript: str,
    report_type: str,
    company_name: str,
    language_output: str,
    detail_level: str,
    privacy_anonymize: bool,
    confidence_labeling: bool,
    pre_briefing_context: str,
    quantitative_data: dict[str, Any] | None,
) -> str:
    quantitative_text = (
        json.dumps(quantitative_data, ensure_ascii=False, indent=2)
        if quantitative_data
        else "없음"
    )

    meeting_template = """
#### [회의/워크숍 분석 보고서]
1. 회의 개요
2. 데이터 기반 동향 분석
3. 주요 발견사항 및 심층 분석
4. 실행 가능한 가설
5. 실행 계획 (RASCI 매트릭스)
6. 사고체인·상식 검증 요약
7. 부록
"""

    interview_template = """
#### [1:1 인터뷰 분석 보고서]
1. 요약 (Executive Summary)
2. 코드별 분석 결과
3. 주요 발견사항
4. 종합 인사이트
5. 리스크 및 기회
6. 사고체인·상식 검증 요약
7. 부록
"""

    selected_template = meeting_template if report_type == "meeting" else interview_template

    return f"""
## 📌 Universal Interview / Meeting Analysis Prompt

### 1. PARAMETERS
- Company_Name: \"{company_name}\"
- Language_Output: \"{language_output}\"
- Output_Detail_Level: \"{detail_level}\"
- Privacy_Anonymize: {str(privacy_anonymize).lower()}
- Confidence_Labeling: {str(confidence_labeling).lower()}
- Pre_briefing_Context: \"{pre_briefing_context}\"
- Quantitative_Data:
{quantitative_text}

### 2. INPUT TRANSCRIPT
INPUT_TRANSCRIPT_START
<<<
{transcript}
>>>
INPUT_TRANSCRIPT_END

### 3. EXECUTION PIPELINE & ANALYSIS FRAMEWORKS
- STAGE 1. 발화 단위 분리 및 코드 매핑 (Pain/Gain/Action), 감성 흐름 분석, 개체/관계 분석
- STAGE 2. SWOT 분석, RASCI 매트릭스 초안 생성
- STAGE 3. 실행 가능한 가설 2~3개 도출, 모든 인사이트는 인용/데이터 근거 포함

### 4. FINAL OUTPUT TEMPLATES
{selected_template}

### 작성 지침
- 출력은 반드시 한국어로 작성
- Privacy_Anonymize=true면 이름/개인정보를 비식별 처리
- Confidence_Labeling=true면 핵심 주장마다 Evidence Strength(A/B/C) 라벨 명시
- 표는 Markdown 표 형식으로 작성
- 발언 인용은 타임스탬프를 포함해 제시
""".strip()


def build_analysis_report(client: OpenAI, prompt: str) -> str:
    response = client.responses.create(model=ANALYSIS_MODEL, input=prompt)
    return response.output_text.strip()


def save_outputs(output_dir: Path, transcript: str, report: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    transcript_path = output_dir / f"transcript_{ts}.txt"
    report_path = output_dir / f"analysis_report_{ts}.md"

    transcript_path.write_text(transcript, encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")

    return transcript_path, report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="음성 파일을 녹취록/분석 보고서로 변환하는 도구"
    )
    parser.add_argument("audio", type=Path, help="입력 오디오 파일 경로(mp3, wav, m4a 등)")
    parser.add_argument("--company", type=str, default="신한정밀공업")
    parser.add_argument("--language", type=str, default="ko")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument(
        "--report-type",
        choices=["meeting", "interview"],
        default="meeting",
        help="분석 보고서 유형 선택",
    )
    parser.add_argument(
        "--detail-level",
        choices=["Summary", "Exhaustive"],
        default="Exhaustive",
    )
    parser.add_argument("--pre-briefing-context", type=str, default="없음")
    parser.add_argument("--quant-data", type=Path, default=None, help="정량 데이터 JSON 파일")
    parser.add_argument(
        "--no-anonymize",
        action="store_true",
        help="개인정보 비식별화를 비활성화",
    )
    parser.add_argument(
        "--no-confidence-label",
        action="store_true",
        help="Evidence Strength 라벨링 비활성화",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    if not args.audio.exists():
        raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {args.audio}")

    quantitative_data = load_quantitative_data(args.quant_data)

    client = OpenAI()

    print("[1/3] 오디오를 녹취록으로 변환 중...")
    transcript = transcribe_audio(client, args.audio, args.language)

    print("[2/3] 범용 분석 프롬프트로 보고서 생성 중...")
    prompt = build_analysis_prompt(
        transcript=transcript,
        report_type=args.report_type,
        company_name=args.company,
        language_output=args.language,
        detail_level=args.detail_level,
        privacy_anonymize=not args.no_anonymize,
        confidence_labeling=not args.no_confidence_label,
        pre_briefing_context=args.pre_briefing_context,
        quantitative_data=quantitative_data,
    )
    report = build_analysis_report(client, prompt)

    print("[3/3] 파일 저장 중...")
    transcript_path, report_path = save_outputs(args.output_dir, transcript, report)

    print("\n완료!")
    print(f"- 녹취록: {transcript_path}")
    print(f"- 분석 보고서: {report_path}")


if __name__ == "__main__":
    main()
