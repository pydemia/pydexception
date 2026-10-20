# pydexception v1 구현 계획

기준 문서: [기획안](plan.md), [재검토 기록](plan-review.md). 현재 완료·검증 범위는 [검증 기록](verification.md)에 있다. 구현 범위는 이 저장소의 배포 가능한 Python 패키지와 예제다. `/Users/a09255/git/skax-successionX-backend`는 기존 계약을 확인하는 참조 저장소로 사용한다. 서비스의 예외 교체와 배포는 패키지 검증 이후의 별도 변경이다.

## 이번 구현에서 고정할 계약

| 영역 | v1 계약 |
| --- | --- |
| 오류 정의 | `ErrorSpec`은 Pydantic 2의 불변 모델이다. 업무 `code`는 비어 있지 않은 문자열 또는 `bool`이 아닌 정수이고, `http_status`는 400~599다. `type_uri`, `title`, 공개용 `message`를 필수로 둔다. |
| 카탈로그 | 앱별 `ErrorCatalog`에 등록한 정의는 코드 중복을 거부한다. 등록하지 않은 `ErrorSpec`도 `AppException`에 직접 사용할 수 있지만, 중복 검사는 등록된 범위에만 적용된다고 문서화한다. 같은 유형 URI의 제목·상태 규칙과 `about:blank` 예외를 검증한다. |
| 예외 | `AppException(Exception)`은 정의, 공개 가능한 요청별 `detail`, 응답 헤더를 가진다. 내부 원인은 예외 체인으로만 유지한다. 기존 `HandledException`과의 상속·속성 호환은 제공하지 않는다. |
| 오류 변환 | 예외 종류를 분류해 HTTP 상태, 업무 코드, 공개 문구, 헤더를 가진 요청별 값으로 만든다. 이 단계는 응답 JSON 조립 및 로깅과 분리한다. |
| 기본 응답 | `application/problem+json`에 `type`, `title`, `status`, `detail`, `code`, `trace_id`를 담는다. 요청별 설명이 없으면 `ErrorSpec.message`를 `detail`로 사용한다. `instance`는 공급자가 오류 발생별 URI reference를 제공할 때만 포함한다. |
| FastAPI 연결 | `install_exception_handlers(...)`가 `AppException`, Starlette `HTTPException`, `RequestValidationError`, 일반 `Exception`을 처리한다. 기본 핸들러 교체와 서비스 사용자 핸들러 충돌을 구별한다. 앱별 상태만 저장한다. |
| 확장 | 서비스용 예외 매핑과 응답 렌더러를 주입할 수 있다. 패키지에는 기존 백엔드 전용 카탈로그·설정·DB 분기를 넣지 않는다. |

모듈 경계는 모델·카탈로그·예외, 순수 변환, 응답 렌더러, FastAPI 연결, OpenAPI 보조 함수로 나눈다. 공개 import는 최상위 패키지에 모으되 내부 모듈의 이름을 공개 API로 약속하지 않는다. 변환 결과는 요청별 불변 값으로 만들어 라우트 래퍼와 전역 핸들러가 같은 분류 규칙을 사용할 수 있게 한다.

## 작업 순서와 통과 조건

### 1. 기존 응답 기준선

- 기존 백엔드의 `HandledException`, 전역 핸들러, `RequestLoggingRoute`, 응답 모델과 소비 호출부를 다시 확인하고 `docs/compatibility-matrix.md`에 대표 사례를 기록한다.
- 최소 사례: 음수 코드 `-1001`의 상태 결정과 응답 문자열 `"-1001"`, 요청 검증 오류의 HTTP `400`/본문 문자열 `"422"`, 라우트 안팎 404·405, 인증 관련 헤더, 본문 `log-*`와 헤더 `trn-*`, 기존 봉투의 필드 경로.
- 실행 가능한 서비스 테스트를 돌려 관측값을 채운다. 실행 환경이 부족한 사례는 소스에서 추론한 값과 미검증 이유를 따로 표시한다. 테스트 파일에 적힌 기대값을 실행 증거로 바꾸지 않는다.

### 2. 패키지 골격과 모델

- `pyproject.toml`, `src/pydexception/`, `py.typed`, README, 예제, 테스트 구성을 만든다. 초기 대상은 Python 3.10~3.13과 Pydantic 2/FastAPI 조합이다. 실제 통과 조합에 맞춰 의존성 하한·상한을 정한다.
- `ErrorSpec`, `ErrorCatalog`, `AppException`, RFC 9457 응답 모델을 구현한다. URI reference 검증, `about:blank`, 코드의 문자열/정수 자료형, 불변 정의, 카탈로그 중복을 테스트한다.
- 공개 API는 `pydexception` 최상위 import 예제와 타입 검사로 고정한다. 패키지 import 시 외부 서비스 설정이나 로거를 초기화하지 않는다.

### 3. 변환과 FastAPI 어댑터

- 공통 변환 함수에서 `AppException`, Starlette `HTTPException`, 요청 검증 오류, 알 수 없는 예외를 분류한다. 내부 Pydantic `ValidationError`는 요청 검증 오류로 오인하지 않는다.
- 기본 렌더러와 선택적 렌더러 인터페이스를 구현한다. 실제 HTTP 상태와 본문 `status`의 일치, `Content-Type`, 헤더 보존, 요청 ID의 본문·헤더 일치를 보장한다.
- `install_exception_handlers`는 같은 앱의 중복 설치와 서비스 사용자 핸들러 충돌을 검사한다. 3xx 등 비오류 `HTTPException`은 FastAPI의 기존 처리에 위임한다. 오류 처리 과정에서 다시 예외가 발생했을 때의 500 경로도 검사한다.
- 공개 검증 오류에는 기본 안내만 담는다. 선택적으로 필드 목록을 넣는다면 `loc`·`type` 등 허용 필드만 사용하고 `input`, 본문, 내부 `ctx`는 제외한다. 기본 로그에는 요청 헤더·본문·query·원본 예외 문자열을 넣지 않는다.

### 4. 문서·호환 예제

- `problem_responses(...)`로 경로별 OpenAPI 오류 응답을 선언하고 생성된 OpenAPI 문서의 schema, media type, 예시를 테스트한다.
- 최소 FastAPI 앱과 사용자 정의 오류, HTTP 오류, 요청 검증 오류, 예외 매핑 예제를 작성한다. `RequestLoggingRoute`처럼 예외를 먼저 처리하는 라우트에서 공통 변환 함수를 호출하는 방법을 별도 예제로 보여준다.
- 기존 봉투의 호환 렌더러는 서비스 어댑터 예제로 제공한다. `-1001`을 HTTP `500`으로 유지하는 경우와 `404`로 바꾸는 경우를 서로 다른 이전 시나리오로 적는다. 어댑터 예제를 실제 서비스의 전체 호환성으로 표현하지 않는다.

### 5. 검증과 완료 판정

- 단위 테스트: 모델 검증, 등록 충돌, 두 요청 사이의 정의·응답 독립성, 예외 매핑 우선순위, 내부 정보 비노출.
- TestClient 통합 테스트: 404·405, 401의 `WWW-Authenticate`, 429의 `Retry-After`, 요청 검증 422, 500, 3xx 위임, 기존 핸들러 충돌, 요청 ID와 `Content-Type`. 500 본문을 검사할 때는 `raise_server_exceptions=False`를 사용한다.
- wheel·sdist를 빌드하고 새 환경에 wheel을 설치해 예제 앱을 실행한다. 타입 검사와 lint를 실행한다. 지원 Python과 FastAPI/Pydantic 최소·최신 조합의 CI workflow를 작성하고 로컬에서 실행 가능한 조합을 확인한다. 원격 CI는 실제 실행된 경우에만 통과를 보고한다.
- 완료 보고에는 구현 파일, 실행한 명령과 결과, 남은 미검증 범위, 기존 서비스 이전에 필요한 결정을 분리해 적는다. 검사 통과만으로 기존 서비스 호환 완료를 주장하지 않는다.

## 구현 중 결정 기준

- 구현 선택이 기존 HTTP 상태나 응답 필드 경로를 바꾸면 `docs/compatibility-matrix.md`에 현재값·새값·소비 영향을 먼저 적는다.
- 공개 API를 추가할 때는 최소 앱 예제로 실제 사용 경로를 확인한다. 편의를 위한 별칭과 패키지 전역 설정은 필요성이 확인될 때만 추가한다.
- `ErrorSpec`의 등록 여부, 요청별 `detail`, 원본 예외, 검증 입력은 클라이언트와 로그에 노출되는 경계를 각각 검사한다.
- 서비스 이전 결정을 요구하는 항목은 문서에서 미결로 유지하고 패키지의 안전한 기본 동작부터 완성한다.

## 근거

- [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html): Problem Details 멤버와 문제 유형 정의.
- [FastAPI 오류 처리](https://fastapi.tiangolo.com/tutorial/handling-errors/): Starlette `HTTPException` 등록, 요청 검증 핸들러, 기존 핸들러 재사용.
- [Starlette TestClient](https://starlette.dev/testclient/): 500 응답 검사 시 `raise_server_exceptions=False`.
