
# Stock-service

## 시스템 설계
https://docs.google.com/document/d/1vjqFi6cl6GLM0W6V_sZaQuIGTlxnmx6wV-aPxnC4YfE/edit?usp=sharing


## 목차
1. [프로젝트 실행 방법](#프로젝트-실행-방법)
2. [테스트 실행 방법](#테스트-실행-방법)
3. [API 문서](#API-문서)

### Python 버전
이 프로젝트는 Python의 LTS인 3.11에서 만들어졌습니다.

## 프로젝트 실행 방법
프로그램을 실행하기 위해선 다음과 같은 절차를 따릅니다.

### 프로젝트 클론:
```bash
# 해당 프로젝트를 클론합니다.
git clone https://github.com/h32109/stock-service.git
```
### 필요 라이브러리 설치:
```bash
# 필요한 라이브러리를 설치합니다.
pip install -r requirements.txt

```
### 환경 변수 설정:
```bash
# 환경 변수 설정
export TRADER_ENVIRONMENT="prod"

# 한국투자증권 OPEN API KEY 설정
stock-service/config/trader/.secrets.toml
...
[prod.kis]
app_key="YOUR_APP_KEY"
secret_key="YOUR_SECRET_KEY"
...
```

### 애플리케이션 실행:
```bash
# 애플리케이션을 시작합니다.
uvicorn main:app --lifespan=on
```

## 테스트 실행 방법
테스트 실행하기 위해선 다음과 같은 절차를 따릅니다.
### 필요 라이브러리 설치:
```bash
# 필요한 라이브러리를 설치합니다.
pip install -r requirements-test.txt
```

### 테스트 실행:
```bash
# 테스트를 시작합니다.
pytest --asyncio-mode=auto
```

## API 문서
이 프로젝트의 API 문서 openapi swagger로 작성되어 있습니다.  
파일 경로는 다음과 같습니다.  
홈페이지 참고: https://editor.swagger.io/

```bash
stock-service/openapi.yaml
```
