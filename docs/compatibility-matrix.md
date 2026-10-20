# 기존 백엔드 오류 응답 기준선

기준 소스: `/Users/a09255/git/skax-successionX-backend`, 로컬 `develop`의 `45e2e2907`. 실행 환경: `agentstore/.venv`의 Python 3.13.12, FastAPI 0.135.2, Pydantic 2.12.5, Starlette 0.50.0, httpx 0.28.1. `scripts/capture_legacy_baseline.py`를 해당 환경과 백엔드 루트 `PYTHONPATH`로 실행한 **합성 TestClient 요청**의 결과다. 운영 서비스, 실제 클라이언트, 배포 설정에서 확인한 결과는 아니다.

| 사례 | 실행 확인한 기존 HTTP/본문/헤더 | 근거와 신규 기본값 또는 이전 판단 |
| --- | --- | --- |
| `RequestLoggingRoute` 안의 요청 검증 실패 | HTTP `400`; JSON의 `detail.status`는 문자열 `"422"`; 본문 `trace_id`는 `log-*`, 헤더 `X-Request-ID`는 `trn-*`; `application/json` | `shared/exception/exception_response.py:37-38`, `exceptions.py:269-278`, `shared/logging/routes.py:69-79`. 신규 기본값은 HTTP·본문 `422`, 같은 요청 ID를 본문과 헤더에 쓴다. 기존 API를 전환할 때 상태와 필드 경로 변경을 별도 승인·검증한다. |
| `HandledException(ErrorCatalog.ENTITY_NOT_FOUND.value)` | HTTP `500`; JSON의 `detail.status`는 문자열 `"-1001"`; 본문 `log-*`, 헤더 `trn-*`; `application/json` | `shared/exception/types/error_catalog.py:21-26`, `exceptions.py:267-278`. 새 정의를 404로 만들면 HTTP 계약이 달라진다. 코드 이름만 보고 자동으로 바꾸지 않는다. |
| 라우트 안의 `HTTPException(401, headers={"WWW-Authenticate": "Bearer"})` | HTTP `401`; JSON의 `detail.status`는 문자열 `"-1000"`; `WWW-Authenticate` 헤더 없음; `application/json` | `shared/exception/exception_response.py:35-45`와 `exception_handlers.py:33-42`가 원본 헤더를 전달하지 않는다. 새 기본 핸들러는 유효한 헤더를 보존한다. |
| 일치하는 경로가 없는 404 | HTTP `404`; 기존 공통 봉투가 아닌 FastAPI 기본 `detail` 본문; `X-Request-ID` 없음; `application/json` | 라우트 래퍼가 호출되지 않고 현재 전역 핸들러는 FastAPI `HTTPException`에 등록된다. 새 어댑터는 Starlette `HTTPException`을 처리한다. |
| 경로는 있으나 메서드가 다른 405 | HTTP `405`; FastAPI 기본 `detail` 본문; `Allow: GET`; `X-Request-ID` 없음; `application/json` | 새 어댑터는 `Allow`를 보존하면서 Problem Details로 변환한다. |

합성 실행에서 라우트 안의 앞 세 사례는 모두 최상위 `data`, `detail`, `payload`, `timestamp`, `trace_id`를 반환했다. `timestamp`는 JSON 정수이고 `data`·`payload`는 `null`이었다. 중첩 `detail`에는 `type`, `title`, `status`, `detail`, `instance`, `system_message` 필드가 있었다. `system_message`의 값은 환경 정책에 따라 달라지므로 아래에는 기록하지 않았다.

| 사례 | 실행 확인한 본문 문구·경로 | 추가 헤더 |
| --- | --- | --- |
| 라우트 검증 실패 | `detail.title="Request Validation Error"`, `detail.detail="요청이 올바르지 않습니다. 입력값을 확인해주세요."`, `detail.instance="/items"` | `X-Request-Time`, `X-Response-Duration` 있음 |
| `ENTITY_NOT_FOUND` | `detail.title="Entity Not Found"`, `detail.detail="Entity를 찾을 수 없습니다."`, `detail.instance="/items"` | `X-Request-Time`, `X-Response-Duration` 있음 |
| 라우트의 HTTP 401 | `detail.title="Undefined Error"`, `detail.detail="정의되지 않은 오류가 발생했습니다."`, `detail.instance="/protected"` | `X-Request-Time`, `X-Response-Duration` 있음 |
| 일치 경로 없는 404 | 본문은 `{"detail":"Not Found"}` | 위 라우트 헤더 없음 |
| 메서드 405 | 본문은 `{"detail":"Method Not Allowed"}` | `Allow: GET`; 위 라우트 헤더 없음 |

자료형의 원인은 `shared/types/common/base.py:7-20`의 `json_encoders={int: str, ...}`다. Pydantic 모델의 `ErrorDetail.status` 타입은 `int`지만 JSON 응답에서는 문자열이다. `agentstore/mainapp/domains/agents/nudge/tools.py:179-189`의 TODO는 문자열 비교가 실패한다고 적었으나 이 합성 실행과는 맞지 않는다. 실제 `/nudge/question` 호출 경로는 이번 기준선에서 실행하지 않았으므로 그 분기의 동작은 별도로 확인해야 한다.

추가 소스 근거: `shared/types/schema/response.py:77-127`의 오류 봉투는 `timestamp`, 중첩 `detail`, `trace_id`, `data`, `payload`를 포함한다. `shared/exception/error_detail.py:65-69`의 `system_message` 직렬화는 환경 설정에 따라 달라진다. 위 합성 실행에서 전체 본문 필드와 로그의 운영 설정별 변형은 비교하지 않았다. 기존 봉투를 완전히 보존한다고 주장하려면 대상 서비스·환경별 실행 확인이 더 필요하다.

재현 예시:

```bash
PYTHONPATH=/Users/a09255/git/skax-successionX-backend \
  /Users/a09255/git/skax-successionX-backend/agentstore/.venv/bin/python \
  /Users/a09255/git/pydexception/scripts/capture_legacy_baseline.py
```

스크립트는 TestClient에서 만든 합성 입력만 보내며 실제 서비스나 네트워크를 호출하지 않는다. 결과에는 요청·응답의 식별자 전체와 로그 본문을 출력하지 않는다.
