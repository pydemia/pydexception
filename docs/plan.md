# pydexception 기획안

상태: v1 설계 기준. 구현과 검증 결과는 [검증 기록](verification.md), 기존 응답의 합성 실행 결과는 [호환성 기준선](compatibility-matrix.md)에 있다. 기존 동작의 소스 기준은 2026-10-20 `/Users/a09255/git/skax-successionX-backend` 로컬 `develop`(`45e2e2907`)이다. 현재 로컬 추적 참조 `origin/develop`(`d73fb477c`)과 비교했을 때 검토한 예외·응답·로깅 파일에는 차이가 없다.

## 목적

FastAPI 서비스가 오류 정의, 발생, HTTP 응답 변환을 같은 규칙으로 다루게 한다. Pydantic은 오류 정의와 응답 본문을 검증한다. 서비스별 업무 오류는 서비스가 소유하며, 패키지는 그 정의를 등록하고 예외를 응답으로 바꾸는 기능을 제공한다.

오류 계약에는 서로 다른 세 값이 있다.

| 값 | 의미 | 예 |
| --- | --- | --- |
| HTTP 상태 | 프로토콜상의 결과. 응답 상태줄과 본문 `status`가 일치해야 한다. | `404` |
| 응답 코드 `code` | 클라이언트가 분기할 안정적인 업무 식별자. 문자열 또는 기존 음수 정수를 허용한다. | `entity_not_found`, `-1001` |
| 문구 | `title`은 오류 유형의 짧은 이름, `message`는 안전한 기본 안내, `detail`은 해당 요청에만 해당하는 선택적 설명이다. | `Entity Not Found`, `항목을 찾을 수 없습니다.` |

## 기존 코드에서 확인한 계약과 문제

기준 코드는 `shared/exception/{error_detail.py,exceptions.py,exception_handlers.py,exception_response.py,middlewares.py,types/error_catalog.py}`, `shared/types/schema/response.py`, `shared/logging/routes.py`다.

| 기존 동작 | 패키지 설계에 반영할 점 |
| --- | --- |
| `ErrorCatalog`가 `ErrorDetail`을 담고 `HandledException`이 이를 감싸며, 여러 서비스에서 `set_message()`로 요청별 문구를 만든다. | 카탈로그 정의와 요청별 오류 인스턴스를 분리한다. 기존 업무 코드와 문구는 서비스가 소유하고 가져온다. |
| `ErrorDetail.status`는 `-1000`대 업무 코드를 허용한다. 명시 상태가 없는 `-1001`은 HTTP `500`으로 폴백한다. 공통 JSON encoder가 모델의 정수 `status`를 응답에서 문자열로 만든다. | 업무 코드는 `code`, HTTP 상태는 `http_status`/본문 `status`로 분리한다. 기존 봉투의 문자열 자료형과 경로별 HTTP 상태를 각각 기록한다. |
| `ErrorCatalog.*.value`는 변경 가능한 Pydantic 모델이다. `HandledException`이 `system_message`를 쓰고 응답 조립이 `instance`를 쓴다. `set_message()`를 거치지 않은 경로도 있다. | 정의를 불변으로 만들고 매 요청마다 새 응답 모델을 생성한다. 공유 카탈로그 값을 응답 생성 과정에서 수정하지 않는다. |
| `RequestLoggingRoute`는 예외를 잡아 직접 응답을 만들므로 전역 핸들러보다 먼저 변환한다. 이 경로의 요청 검증 오류는 카탈로그 코드 `422`를 담아 HTTP `400`으로 응답한다. | 두 경로가 같은 변환 함수를 사용하도록 이전한다. 새 기본값 `422`와 기존 `400`의 차이는 호출부별로 확인한다. |
| `ErrorResponse`는 `timestamp`, 중첩된 `detail`, `trace_id`, `data`, `payload`를 가진 프로젝트 응답 봉투다. 오류 본문의 `trace_id`는 예외가 발급한 `log-*`이고 라우트의 `X-Request-ID`는 `trn-*`이다. | 패키지 기본 응답과 기존 봉투를 구분한다. 성공 응답·페이지네이션은 패키지 범위에서 제외한다. 호환 렌더러는 ID·헤더 계약까지 확인한다. |
| `get_request_info()`는 요청 헤더와 본문을 로그 문자열에 포함하고, `system_message`는 환경 설정에 따라 직렬화된다. | 패키지 기본 로그에는 요청 본문·인증 헤더·원본 예외 문자열을 넣지 않는다. 클라이언트 본문에 내부 메시지와 스택을 넣지 않는다. |
| 핸들러가 FastAPI의 `HTTPException`에 등록되어 있고, `BackgroundTaskExceptionMiddleware`는 이미 시작된 응답 뒤의 예외를 로깅한다. | Starlette의 `HTTPException`에도 적용되도록 등록한다. 응답이 시작된 뒤에는 본문을 바꾸지 않는 별도 관찰 경로로 취급한다. |
| 오류 유형 URI의 기반값이 `shared.config.app_config`에서 import 시점에 정해진다. | 패키지 import는 서비스 설정을 읽지 않는다. URI와 요청 ID 공급자는 앱에 설치할 때 전달한다. |
| 호출부가 `HandledException`을 잡거나 `.error_detail`, `.message`, `.status_code`를 직접 읽는다. | 새 예외로 단순 치환하지 않는다. 호출부와 하위 클래스를 조사해 단계적으로 이전한다. |

`is_pgcrypto_decryption_error`, 인가 오류의 세부 클래스, `RequestLoggingRoute`의 접근 감사 기능은 현재 서비스 고유 정책이다. 패키지로 옮기지 않고 서비스가 오류 매핑 또는 로깅 훅으로 연결한다.

`data-management/test/domains/authz/test_access_scopes.py:168-179`에는 HTTP `400`을 기대하는 테스트가 있다. 별도의 합성 TestClient 실행에서도 라우트 검증 오류의 HTTP `400`을 확인했다. `agentstore/mainapp/domains/agents/nudge/tools.py:179-189`의 TODO는 `"-1001"` 문자열 비교가 실패한다고 설명하지만 합성 응답의 `detail.status`는 문자열이다. 실제 nudge 호출 경로는 실행하지 않았으므로 TODO의 판단과 해당 분기의 동작은 미검증으로 둔다.

## 공개 계약 제안

### 오류 정의와 발생

`ErrorSpec`은 불변 Pydantic 모델이다. 필드는 `code: str | int`, `http_status: int`, `type_uri: str`, `title: str`, `message: str`다. `http_status`는 v1에서 `400..599`로 제한한다. `code`는 빈 문자열과 `bool`을 거부한다. `type_uri`는 RFC 9457의 URI reference를 허용하며, 서비스 고유 유형에는 안정적인 절대 URI를 권장한다. 상대 URI는 응답 위치에 따라 다른 유형으로 해석될 수 있다. `about:blank`도 허용하고 이 경우 `title`은 HTTP 상태 문구를 따른다. 같은 앱 카탈로그의 중복 `code`는 거부한다. 서로 다른 코드가 같은 문제 유형 URI를 공유할 수 있으므로 `type_uri` 고유성은 요구하지 않는다. 같은 절대 URI를 공유하는 서비스 고유 유형에는 `title`과 HTTP 상태의 일치를 검사하고, 유형의 의미가 같은지는 서비스가 정의를 검토한다. `about:blank`은 상태별로 제목이 달라지는 예외로 취급한다. 전역 카탈로그를 두지 않고 등록 후 정의를 수정하지 않는다.

`AppException(Exception)`은 `ErrorSpec`과 선택적 `detail`, `headers`를 가진다. `message`는 정의의 공개 가능한 기본 안내이며, `detail`에는 호출자가 공개 가능하다고 판단한 요청별 설명만 넣는다. 원본 예외는 Python의 `raise AppException(...) from exc`로 연결하고 traceback과 함께 응답에 직렬화하지 않는다. 서비스 계층에서 FastAPI 객체 없이 발생시킬 수 있도록 `HTTPException`을 상속하지 않는다. 따라서 기존 `HandledException`의 생성자·상속 관계·속성과 자동 호환되지는 않는다.

사용 예시는 다음과 같다. 정확한 클래스·함수명은 구현 전 API 검토에서 고정한다.

```python
ITEM_NOT_FOUND = ErrorSpec(
    code="item_not_found",
    http_status=404,
    type_uri="https://api.example.com/problems/item-not-found",
    title="Item Not Found",
    message="항목을 찾을 수 없습니다.",
)

raise AppException(ITEM_NOT_FOUND)
```

### 기본 HTTP 응답

기본 렌더러는 `application/problem+json`으로 RFC 9457의 `type`, `title`, `status`, `detail`을 사용한다. 패키지 확장 멤버 `code`, `trace_id`를 추가한다. `status`는 실제 HTTP 상태와 같다. `detail`은 요청별 공개 설명이 있으면 그 값을 쓰고, 없으면 `ErrorSpec.message`를 쓴다. 이 방식이면 일반 Problem Details 클라이언트에도 기본 안내가 보인다. 중복되는 `message` 확장 멤버는 기본 응답에 넣지 않는다. `instance`는 해당 오류 발생을 식별할 URI reference가 공급될 때만 넣는다. 같은 요청 경로에서 여러 오류가 발생할 수 있으므로 경로를 기본 `instance`로 사용하지 않는다.

```json
{
  "type": "https://api.example.com/problems/item-not-found",
  "title": "Item Not Found",
  "status": 404,
  "detail": "항목을 찾을 수 없습니다.",
  "code": "item_not_found",
  "trace_id": "trn-example"
}
```

요청별 `detail`이 필요하면 `AppException(ITEM_NOT_FOUND, detail="...")`로 전달한다. 신규 기본 응답의 `code`는 정의의 문자열·정수 JSON 자료형을 보존한다. 기존 봉투의 `detail.status`는 문자열이므로 이를 신규 `code`로 옮기면 자료형도 바뀔 수 있다. 클라이언트 분기 기준은 `code`이며 문구를 파싱하도록 권하지 않는다.

기존 서비스의 `ErrorResponse` 봉투는 기본 렌더러의 결과가 아니다. `ResponseRenderer` 확장점을 두고 서비스 쪽에서 기존 JSON 구조와 미디어 타입을 만드는 호환 렌더러를 작성한다. 이때 문자열인 `detail.status`, `detail.detail`, `trace_id`, `timestamp`, `data`, `payload`뿐 아니라 HTTP 상태와 응답 헤더도 비교한다. 본문 모양만 맞춰서는 호환성이 성립하지 않는다. 이 렌더러가 `detail.status="-1001"`을 유지하는 동안에는 RFC 9457 응답이라고 표시하지 않는다. 새 형식으로 바꾸는 API는 클라이언트 이전 계획과 함께 별도로 전환한다.

### FastAPI 연결

`install_exception_handlers(app, *, renderer=..., request_id_provider=..., logger=...)`를 제공한다. 앱별 설정을 설치 시점에 전달하고 전역 상태를 두지 않는다. FastAPI가 기본 등록한 핸들러는 교체할 수 있으나 서비스가 직접 등록한 핸들러를 덮어쓰는 경우에는 충돌을 알리고 명시적 `replace=True`를 요구한다. 중복 설치도 검출한다. 핵심 예외 변환 함수는 `RequestLoggingRoute`에서도 재사용할 수 있게 응답 렌더링과 분리한다. 응답 변환의 우선순위는 다음과 같다.

| 입력 | 기본 처리 |
| --- | --- |
| `AppException` | 정의의 HTTP 상태·코드·안전한 문구를 사용한다. 전달된 응답 헤더를 보존하며 `WWW-Authenticate`, `Retry-After`도 검증한다. |
| `starlette.exceptions.HTTPException` | 4xx·5xx에서 원래 HTTP 상태와 `headers`를 보존한다. 기본 문구는 HTTP 상태 문구를 사용하고 원본 `detail` 노출은 앱의 명시적 정책으로만 허용한다. 문자열이 아닌 값의 처리도 문서화한다. 404·405와 `Allow`, `WWW-Authenticate`, `Retry-After` 헤더를 확인한다. 3xx 등 오류가 아닌 상태는 기존 FastAPI 처리로 위임한다. |
| `fastapi.exceptions.RequestValidationError` | HTTP `422`, 고정된 안전 문구를 기본으로 한다. 필드 오류를 노출할 때는 `loc`·`type` 등 허용 필드만 선택하고 `input`, 요청 본문, 내부 `ctx`는 제외한다. |
| 그 밖의 `Exception` | HTTP `500`과 일반 안내 문구를 반환한다. 원본은 로거에 예외 정보로 전달하되 응답에는 넣지 않는다. |

Pydantic `ValidationError`가 서비스 내부에서 발생한 경우를 요청 검증 오류로 자동 취급하지 않는다. 기본값은 `500`이다. 인증·인가·DB 등 서비스별 예외는 명시적 매핑 등록으로 처리한다. 신규 기본값은 `request_id_provider`가 유효한 ID를 주면 본문 `trace_id`와 `X-Request-ID` 헤더에 같은 값을 쓰고, 없으면 요청별로 생성한다. 기존 서비스의 `log-*`와 `trn-*` 분리는 이전 과정에서 별도 계약 변경으로 다룬다. 이미 설정된 헤더와 ID가 다를 때의 처리 규칙을 설치 옵션에서 고정하고 통합 테스트로 확인한다.

기본 로그는 상태, 코드, 요청 ID, 예외 종류 등 구조화된 필드로 제한한다. 요청 헤더·본문, URL query, 원본 예외 문자열은 기본 로그에 넣지 않는다. 원본 예외와 traceback을 운영 로깅에 전달할지는 서비스의 redaction 정책으로 정한다.

WebSocket, SSE 스트림 중간 오류, `BackgroundTask` 실행 중 오류는 HTTP JSON 응답을 보장할 수 없다. v1은 이 경계의 응답을 재작성하지 않는다. 배경 작업 오류를 수집할 필요가 있으면 별도 로깅 훅을 제공하되 기존 미들웨어를 자동 설치하지 않는다.

### 문서화와 배포

- `problem_responses(...)` 보조 함수로 경로별 OpenAPI 오류 응답 스키마와 예시를 선언한다. 핸들러 설치만으로 모든 경로의 OpenAPI 응답이 자동 완성된다고 가정하지 않는다.
- `src/pydexception/` 구조, `py.typed`, `pyproject.toml`, 최소 설치 예제, 기존 서비스 이전 예제를 둔다. 런타임 의존성은 Pydantic 2와 FastAPI로 제한하고 프로젝트 설정·로깅·DB 라이브러리는 포함하지 않는다.
- 초기 지원 목표는 현재 소비 서비스와 겹치는 Python 3.10~3.13이다. FastAPI·Pydantic의 최소/최신 조합은 테스트 행렬을 통과한 뒤 버전 범위로 확정한다.

## 구현 순서와 완료 조건

1. **실행 기준선 고정:** `RequestLoggingRoute` 적용 여부별로 대표 오류의 실제 HTTP 상태·본문·헤더·로그를 TestClient 또는 서비스 통합 테스트로 기록한다. `-1001`의 HTTP `500` 폴백, 검증 오류의 HTTP `400`, 404·405, 인증 헤더, 두 요청 ID를 포함한다. 현재 테스트 파일의 기대값과 코드 추론은 실행 결과로 대체한다.
2. **계약과 이전 매핑 확정:** `ErrorSpec`, `AppException`, 기본 본문 JSON, `message`/`detail` 공개 기준을 고정한다. 기존 코드별로 현재 HTTP 상태와 새 상태를 기록하며, `500`을 `404`로 바꾸는 경로는 클라이언트 영향과 배포 순서를 명시한다.
3. **핵심 구현:** 정의 검증·중복 탐지·요청별 응답 생성·변환 함수·렌더러 인터페이스를 만든다. 카탈로그 원본 불변성과 동시 요청의 독립성을 검사한다.
4. **FastAPI 어댑터:** 오류 종류별 핸들러, 헤더 전달, `trace_id`, OpenAPI 보조 함수를 구현한다. TestClient에서 404·405·401·429 헤더·422·500·3xx 위임·핸들러 충돌·본문/헤더 ID 일치를 검증한다.
5. **서비스 이전:** `RequestLoggingRoute`와 전역 핸들러가 같은 변환 함수를 사용하게 하거나 라우트에서 예외를 전파한다. 후자의 경우 감사 로그와 응답 헤더를 재검증한다. `except HandledException`, `.error_detail`, `.status_code`, `.message`, 하위 클래스 생성자를 사용하는 호출부를 수정한다. 전환 중 필요한 기존 클래스 어댑터는 서비스 쪽에 둔다. 기존 사용처가 남아 있으면 클래스를 제거하지 않는다.
6. **호환·패키지 검증:** 백엔드 오류 사례의 실행 기준선과 호환 렌더러를 비교한다. 의도한 상태·ID 변경은 별도 기대값으로 기록한다. 타입 검사, lint, wheel/sdist 빌드, 설치한 wheel에서 FastAPI 예제 실행, 지원 Python/의존성 조합의 CI를 통과시킨다. 서비스 교체와 패키지 배포는 각각 검증된 범위에서 결정한다.

## 구현 전에 확정할 선택

- `code`를 장기적으로 문자열로 표준화할지, 음수 정수를 계속 공개 계약으로 지원할지. 이 안은 기존 서비스 이전을 위해 둘 다 허용한다.
- 기존 API의 검증 실패 HTTP `400`을 유지할지 `422`로 바꿀지. 패키지 기본값은 `422`이며, 기존 경로의 변경은 클라이언트 영향 확인 후 결정한다.
- 기존 응답 봉투를 계속 유지할 서비스와 RFC 9457 본문으로 바꿀 서비스의 범위. 호환 렌더러는 API별 점진 이전을 전제로 한다.
- 요청별 `detail`과 검증 오류 목록을 외부에 어느 수준까지 공개할지. 기본값은 보수적으로 두고 서비스별 정책을 명시한다.
- 오류 발생별 `instance` URI reference를 제공할지, 제공한다면 생성·조회 규칙을 어떻게 둘지.
- `log-*`와 `trn-*` 중 기존 서비스의 어떤 ID를 이어받을지 및 중복 `X-Request-ID` 처리 규칙.

## 기준 자료

- [RFC 9457: Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)
- [FastAPI 오류 처리 문서](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [Starlette 예외 처리 문서](https://starlette.dev/exceptions/)
