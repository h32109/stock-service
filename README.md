## API Document

### Base URL
```
https://api.stockservice.com
```

### Headers
```http
Accept: application/vnd.stockservice.v1+json
Authorization: Bearer <jwt_token>
```

### Caching Headers
```http
Cache-Control: max-age=3600
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
Last-Modified: Wed, 21 Oct 2024 07:28:00 GMT
```

### 공통 응답 형식
```json
{
    "status": "success" | "error",
    "data": <response_data>,
    "message": "string"
}
```

## HTTP 상태 코드
- 200 OK: 요청 성공
- 201 Created: 리소스 생성 성공 (주문 등)
- 202 Accepted: 비동기 요청 접수
- 304 Not Modified: 캐시된 데이터가 최신
- 400 Bad Request: 잘못된 요청
- 401 Unauthorized: 인증 필요
- 403 Forbidden: 권한 없음
- 404 Not Found: 리소스 없음
- 409 Conflict: 리소스 충돌
- 429 Too Many Requests: 요청 한도 초과
- 500 Internal Server Error: 서버 오류

## API Endpoints

### 주식 검색 API

#### 주식 검색
```http
GET /stocks
```
Query Parameters:
- `q` (string, required): 검색어 (2-5자)
  - 회사명 (예: "삼성전자", "Samsung")
  - 초성 (예: "ㅅㅅㅈㅈ")
  - 종목코드 (예: "005930")
  - 테마명 (예: "반도체", "배터리")
- `page` (integer, optional): 페이지 번호 (기본값: 1)
- `size` (integer, optional): 페이지 크기 (기본값: 20)

Response:
```json
{
    "data": {
        "stocks": [
            {
                "id": "005930",
                "company_name": "삼성전자",
                "company_name_en": "Samsung Electronics",
                "company_name_initial": "ㅅㅅㅈㅈ",
                "security_type": "보통주",
                "market_type": "KOSPI",
                "current_price": 75000,
                "price_change": 1000,
                "volume": 12750000,
                "market_cap": 4470000000000,
                "themes": [
                    {
                        "id": "tech-001",
                        "name": "반도체"
                    }
                ],
                "match_type": ["name", "initial"]
            }
        ],
        "total_count": 150
    }
}
```

#### 개별 주식 조회
```http
GET /stocks/{stock_id}
```

Response:
```json
{
    "data": {
        "id": "005930",
        "company_name": "삼성전자",
        "company_name_en": "Samsung Electronics",
        "company_name_initial": "ㅅㅅㅈㅈ",
        "listing_date": "1975-06-11",
        "market_type": "KOSPI",
        "security_type": "보통주",
        "industry_code": "005930",
        "is_active": true,
        "current_price": 75000,
        "previous_price": 74000,
        "open_price": 74500,
        "high_price": 75500,
        "low_price": 74000,
        "volume": 12750000,
        "price_change": 1000,
        "market_cap": 4470000000000,
        "shares_outstanding": 5969782550,
        "trading_date": "2024-02-02T09:00:00Z",
        "themes": [
            {
                "id": "tech-001",
                "name": "반도체"
            }
        ]
    }
}
```

### 테마 API

#### 테마 목록 조회
```http
GET /themes
```
Query Parameters:
- `parent_id` (string, optional): 상위 테마 ID

Response:
```json
{
    "data": {
        "themes": [
            {
                "id": "tech-001",
                "name": "반도체",
                "parent_id": "tech",
                "child_themes": [
                    {
                        "id": "tech-001-001",
                        "name": "메모리"
                    }
                ]
            }
        ]
    }
}
```

### 계좌 API

#### 계좌 잔고 조회
```http
GET /accounts/{account_id}/balance
```

Response:
```json
{
    "data": {
        "available_balance": 10000000,
        "total_balance": 15000000,
        "locked_balance": 5000000
    }
}
```

#### 보유 주식 조회
```http
GET /accounts/{account_id}/holdings
```

Response:
```json
{
    "data": {
        "holdings": [
            {
                "stock_id": "005930",
                "company_name": "삼성전자",
                "quantity": 100,
                "average_price": 74000,
                "current_price": 75000
            }
        ]
    }
}
```

### 주문 API

#### 매수 주문
```http
POST /orders
```
Request Body:
```json
{
    "type": "buy",
    "stock_id": "005930",
    "quantity": 100,
    "price": 75000
}
```

Response:
```json
{
    "data": {
        "order_id": "b0e7549b-1cc9-4054-9bd4-5f7e33c9e459",
        "type": "buy",
        "stock_id": "005930",
        "requested_quantity": 100,
        "validated_quantity": 100,
        "price": 75000,
        "total_amount": 7500000,
        "status": "pending",
        "remaining_balance": 2500000
    }
}
```

#### 매도 주문
```http
POST /orders
```
Request Body:
```json
{
    "type": "sell",
    "stock_id": "005930",
    "quantity": 50,
    "price": 75000
}
```

Response:
```json
{
    "data": {
        "order_id": "c1f8658c-2dd9-4165-9ce5-6f8e44c9f570",
        "type": "sell",
        "stock_id": "005930",
        "requested_quantity": 50,
        "validated_quantity": 50,
        "price": 75000,
        "total_amount": 3750000,
        "status": "pending",
        "remaining_quantity": 50
    }
}
```

## WebSocket APIs

### 실시간 시세 정보
```
WSS /ws/stocks/prices
```
Subscribe Message:
```json
{
    "action": "subscribe",
    "stocks": ["005930"]
}
```

Price Update Message:
```json
{
    "type": "price_update",
    "data": {
        "stock_id": "005930",
        "current_price": 75100,
        "price_change": 1100,
        "timestamp": "2024-02-02T09:00:01Z"
    }
}
```