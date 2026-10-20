# 기획안 재검토 기록

검토 대상은 이전 `docs/plan.md`와 `/Users/a09255/git/skax-successionX-backend` 로컬 `develop`(`45e2e2907`)이다. 2026-10-20에 업데이트된 `evidence-based-code-review` 스킬의 증거 수준과 구현 계획·수용 조건 분리 기준을 적용했다. 이 기록은 당시 설계 검토이며 이후 구현·실행 결과는 [검증 기록](verification.md)과 [호환성 기준선](compatibility-matrix.md)에 구분해 두었다.

| 이전안의 판단 | 확인한 근거 | 이번 수정 |
| --- | --- | --- |
| 음수 코드와 HTTP 상태를 분리하고 기존 봉투를 렌더러로 유지한다. | `shared/exception/exceptions.py:267-278`: 음수 코드에 명시 상태가 없으면 HTTP `500`. | 렌더러와 별개로 경로별 HTTP 상태 매핑과 실행 기준선을 요구한다. |
| 기존 `ErrorDetail.status`의 정수 타입이 그대로 JSON에 나온다. | 합성 TestClient 응답은 `"-1001"`·`"422"` 문자열이며 `shared/types/common/base.py:7-20`에 `int: str` encoder가 있다. | 호환 봉투의 문자열 자료형과 신규 `code`의 정수 자료형을 별도 계약으로 기록한다. |
| 기본 Problem Details에 `message`를 넣고 `detail`은 요청별 설명이 있을 때만 넣는다. | RFC 9457 §3.1.4에서 일반 클라이언트가 읽는 설명은 `detail`이다. | 기본 안내를 `detail`에 넣고 중복 `message` 확장은 제외한다. |
| 서비스 고유 `type_uri`는 고유해야 한다. | RFC 9457에서 URI는 문제 유형 식별자이며 업무 코드와 1:1이라는 조건은 없다. `about:blank`은 상태별 제목을 쓰는 예외다. | 코드만 고유하게 검사한다. 같은 절대 URI를 공유하는 서비스 유형에는 제목·HTTP 상태를 검사하고 의미는 서비스 정의 검토에서 확인한다. |
| 전역 핸들러를 설치하면 예외 응답이 통일된다. | `shared/logging/routes.py:69-75`가 예외를 먼저 잡아 응답을 만든다. | 라우트와 전역 핸들러의 변환 경로를 함께 이전한다. |
| `AppException(Exception)`으로 기존 예외를 대체한다. | `agentstore/mainapp/domains/agents/adaptive/framework/core/errors.py:40-54` 등에서 기존 예외 속성을 직접 읽는다. | 자동 대체를 주장하지 않고 호출부 이전과 서비스 어댑터를 계획한다. |
| `trace_id`를 `X-Request-ID`에 연결한다. | `shared/exception/exceptions.py:230`, `shared/logging/routes.py:64-79`에서 두 ID를 따로 발급한다. | 신규 기본값과 기존 계약 변경을 분리해 이전 검증에 넣는다. |
| 기본 `instance`에 요청 경로를 쓴다. | RFC 9457 §3.1.5의 `instance`는 해당 오류 발생을 식별한다. | 기본 생략, 공급자가 발생별 URI reference를 줄 때만 포함한다. |

Correctness 관점은 상태·본문·호출부 계약, Security 관점은 내부 문구와 로그 입력, Maintenance 관점은 서비스 정책과 패키지 경계, Setting 관점은 핸들러 설치 충돌과 의존성 범위에 적용했다. 성능 개선 수치와 과거 리뷰 이력은 확인된 자료가 없어 제안하지 않았다. 설계 재검토 시점에는 테스트 파일만 읽었으며, 이후 수행한 합성 TestClient 검증 결과는 별도 기준선에 기록했다.
