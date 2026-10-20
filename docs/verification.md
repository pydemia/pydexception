# pydexception v1 검증 기록

2026-10-20 로컬 작업 결과다. 구현은 `pydexception` 저장소에만 적용했다. 원격 CI와 기존 서비스 배포는 실행하지 않았다.

| 요구 | 현재 증거 | 판정 범위 |
| --- | --- | --- |
| 기존 계약 기준선 | `scripts/capture_legacy_baseline.py`를 백엔드 `agentstore/.venv`로 실행해 5개 합성 TestClient 사례를 확인했다. 결과와 소스 위치는 `docs/compatibility-matrix.md`에 기록했다. | 로컬 합성 요청의 HTTP 상태·일부 본문·헤더 확인. 운영 서비스나 실제 nudge 경로는 미검증. |
| 모델·카탈로그·예외 | `src/pydexception/{models,catalog,exceptions}.py`; URI, 코드/상태 검증, 불변성, 중복, 헤더 검사 테스트. | `pytest` 통과 범위의 동작 확인. |
| 분류·렌더러·FastAPI | `mapping.py`, `renderers.py`, `fastapi.py`; 404·405·401·429·422·500·3xx, 요청 ID, 정보 비노출, 사용자 핸들러 충돌, 라우트 래퍼를 TestClient로 확인. | 새 패키지의 로컬 ASGI 동작 확인. |
| OpenAPI·예제 | `openapi.py`의 `application/problem+json` 문서와 그룹 예시 테스트; `examples/`의 최소 앱, 라우트 래퍼, 기존 봉투 예제 테스트. | 기존 봉투 예제는 이전 방식을 설명하며 실서비스 전체 호환성을 증명하지 않는다. |
| 로컬 테스트 | `uv run --no-sync pytest -q`: 49 passed, 1 warning. | 경고는 현재 설치된 Starlette TestClient의 `httpx` 사용 중단 안내다. 테스트 실패는 아니다. |
| 정적 검사 | `ruff check src examples tests scripts`, `ruff format --check src examples tests scripts`, `mypy src/pydexception examples` 모두 exit 0. | 소스와 예제의 lint·format·타입 검사. |
| 지원 버전 | Python 3.10, 3.11, 3.12, 3.13 각각 최소 FastAPI 0.115.12/Pydantic 2.10.1 조합과 당시 최신 호환 조합을 별도 임시 환경에서 설치했다. 각 8개 조합에서 테스트·lint·format·타입 검사 exit 0. | 로컬 macOS 조합 확인. GitHub Actions 실행 결과는 아니다. |
| 패키징 | `uv build --quiet` exit 0; `dist/pydexception-0.1.0-py3-none-any.whl`, `dist/pydexception-0.1.0.tar.gz` 생성. wheel에 `py.typed` 포함 확인. | 빌드 산출물 확인. PyPI 게시·원격 설치는 하지 않았다. |
| 설치한 wheel 실행 | 새 Python 3.10 최소 의존성 환경과 Python 3.13 최신 의존성 환경에 wheel을 설치했다. 양쪽에서 `examples.minimal_app`의 정상·오류 응답, 미디어 타입, 본문·헤더 요청 ID 일치를 확인했다. | 로컬 설치 스모크 확인. |
| CI | `.github/workflows/ci.yml`에 3.10~3.13 × 최소·최신 의존성 매트릭스, 검사·빌드·wheel 스모크를 정의했다. | workflow 파일 작성. 원격 CI는 아직 실행되지 않았다. |

기존 백엔드에는 `detail.status`가 Pydantic 모델에서는 정수지만 JSON 응답에서는 문자열이 되는 설정(`shared/types/common/base.py:7-20`)이 있다. 새 RFC 9457 기본 응답의 `code`는 정의의 정수·문자열 자료형을 유지한다. 기존 봉투에서 새 응답으로 API를 전환할 때 이 차이를 클라이언트 계약으로 검토해야 한다.
