# SPI Meeting Notes

신한정밀공업 회의 녹음 파일을 업로드(파일 입력)하면 아래를 자동 수행합니다.

1. **녹취록(타임스탬프 포함 텍스트)** 생성
2. **Universal Interview / Meeting Analysis Prompt** 기반 분석 보고서 생성
   - 회의/워크숍 보고서
   - 1:1 인터뷰 보고서

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## API 키 설정

`.env` 파일 생성:

```bash
OPENAI_API_KEY=sk-...
```

## 실행

기본(회의 보고서):

```bash
python app.py /path/to/meeting_audio.m4a
```

고급 옵션 예시:

```bash
python app.py /path/to/meeting_audio.m4a \
  --company "신한정밀공업" \
  --language ko \
  --report-type meeting \
  --detail-level Exhaustive \
  --pre-briefing-context "1차 조직 개편안 발표 후 피드백 수렴" \
  --quant-data ./quant_data.json \
  --output-dir outputs
```

인터뷰 보고서:

```bash
python app.py /path/to/interview_audio.m4a --report-type interview
```

## 정량 데이터(JSON) 예시

```json
{
  "speaker_metrics": {
    "CEO": {"count": 50, "duration_sec": 1800},
    "HR": {"count": 34, "duration_sec": 1200}
  },
  "keyword_frequency": {
    "리더십": 25,
    "성과 평가": 18
  }
}
```

## 결과물

`outputs/` 폴더에 생성:

- `transcript_YYYYMMDD_HHMMSS.txt`
- `analysis_report_YYYYMMDD_HHMMSS.md`

## 분석 반영 항목

- Pain / Gain / Action 코드 매핑
- 감성 흐름 및 개체/관계 분석
- SWOT 분석
- RASCI 매트릭스
- 실행 가능한 가설(근거 인용 포함)
- Evidence Strength(A/B/C)
- 비식별화(옵션)
