# Goal 생성용 메시지

아래 문구를 새 메시지로 보내면 구현 목표와 완료 기준을 함께 지정할 수 있다.

```text
Goal을 생성하고 완료될 때까지 진행해 주세요.

목표: /Users/a09255/git/pydexception에서 docs/plan.md와 docs/implementation-plan.md를 기준으로 FastAPI·Pydantic 2용 pydexception v1 Python 패키지를 구현합니다. ErrorSpec, 앱별 ErrorCatalog, AppException, RFC 9457 기본 응답, 공통 예외 분류, 렌더러 확장점, FastAPI 핸들러 설치, OpenAPI 응답 보조 함수, 타입 정보, 패키징과 실행 가능한 사용 예제를 완성합니다.

기존 계약: /Users/a09255/git/skax-successionX-backend의 현재 예외·응답 코드를 참조해 대표 사례의 HTTP 상태, 본문, 헤더, 요청 ID를 docs/compatibility-matrix.md에 기록합니다. 실제 실행 결과와 소스에서 추론한 값을 구분합니다. 기존 서비스 코드 교체와 배포는 이 목표의 완료 조건에 포함하지 않습니다.

완료 기준: 모델과 카탈로그 검증, 오류 분류, 헤더·요청 ID, 내부 정보 비노출을 테스트합니다. TestClient 통합 테스트, wheel·sdist 빌드, 새 환경에 설치한 wheel의 예제 실행, 타입 검사와 lint를 완료합니다. 지원 버전 CI workflow를 작성하고 로컬에서 실행 가능한 조합을 확인합니다. 원격 CI는 실제 실행된 경우에만 통과로 기록합니다. 단계별 진행 상황, 통과한 검사, 미실행·실패 항목과 남은 조건을 보고하고 검증되지 않은 항목을 완료로 표시하지 않습니다.
```
