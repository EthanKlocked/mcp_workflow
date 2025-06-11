# AI Workflow with MCP

MCP(Model Context Protocol) 서버와 클라이언트를 활용한 AI 에이전트 워크플로우 시스템

## 🚀 주요 기능

-   **MCP 서버**: Bitget API를 MCP 도구로 제공
-   **LangChain 에이전트**: MCP 도구를 활용한 AI 에이전트
-   **암호화폐 거래**: 실시간 가격 조회, 주문 생성/취소, 포지션 관리
-   **워크플로우 자동화**: AI 에이전트 기반 거래 전략 실행

## 📁 프로젝트 구조

```
ai_workflow/
├── src/
│   ├── ability/module/
│   │   └── bitget_trader.py      # Bitget API 클라이언트
│   ├── core/
│   │   ├── mcp_client.py         # MCP 클라이언트 (HTTP 기반)
│   │   ├── mcp_server.py         # MCP 서버 (Bitget 도구 제공)
│   │   └── langchain_agent.py    # LangChain 에이전트
│   ├── operator/trader/
│   │   └── workflow.py           # 거래 워크플로우
│   └── test/
│       └── test.ipynb            # 테스트 노트북
├── pyproject.toml                # Poetry 설정
├── .env.example                  # 환경변수 템플릿
└── README.md
```

## 🛠️ 설치 및 실행

### 1. 환경 설정

```bash
# Python 가상환경 생성 (pyenv 사용)
pyenv virtualenv 3.12.3 ai_workflow
pyenv activate ai_workflow

# 의존성 설치
poetry install
```

### 2. 환경변수 설정

```bash
# 환경변수 파일 생성
cp .env.example .env
```

`.env` 파일에 다음 내용 설정:

```bash
# MCP 서버 설정
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8000

# OpenAI API (LangChain 에이전트용)
OPENAI_API_KEY=your_openai_api_key

# Bitget API 설정
BITGET_API_KEY=your_bitget_api_key
BITGET_SECRET_KEY=your_bitget_secret_key
BITGET_PASSPHRASE=your_bitget_passphrase
```

### 3. MCP 서버 실행

```bash
# MCP 서버 시작
python src/core/mcp_server.py
```

서버 실행 후 다음과 같은 메시지가 표시됩니다:

```
INFO: Starting MCP server 'mcp-tools-server' with transport 'streamable-http' on http://localhost:8000/mcp
```

### 4. AI 에이전트 테스트

Jupyter Notebook에서 `src/test/test.ipynb` 실행:

```python
# 에이전트 생성 및 테스트
from langchain_agent import LangChainAgent
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def test_agent():
    agent_client = LangChainAgent(model_key="gpt4mini")

    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 에이전트 생성
            agent = await agent_client.create_agent(session, "trading_agent")

            # 질문 테스트
            answer = await agent_client.ask_agent("비트코인 현재 가격을 알려줘", "trading_agent")
            print(answer)

await test_agent()
```

## 🔧 주요 MCP 도구들

### 계정 및 포지션 관리

-   `get_bitget_account_info()` - 계정 잔고 및 정보 조회
-   `get_bitget_positions()` - 현재 포지션 목록 조회
-   `show_position_details()` - 포지션 상세 정보 조회

### 시장 데이터

-   `get_bitget_price(symbol)` - 특정 코인 현재 가격 조회
-   `get_bitget_candles(symbol, interval, limit)` - 캔들스틱 차트 데이터

### 주문 관리

-   `place_bitget_order(symbol, side, quantity, type, price)` - 주문 생성
-   `cancel_bitget_order(symbol, order_id)` - 주문 취소
-   `get_bitget_open_orders(symbol)` - 미체결 주문 조회
-   `get_bitget_order_history(symbol, limit)` - 거래 내역 조회

### 포지션 청산

-   `close_bitget_position_correct(symbol)` - 특정 포지션 청산
-   `close_all_bitget_positions_correct()` - 모든 포지션 청산

### 계정 설정

-   `set_bitget_leverage(symbol, leverage)` - 레버리지 설정

## 💡 사용 예시

```python
# AI 에이전트에게 질문 예시
questions = [
    "현재 계정 잔고를 확인해줘",
    "비트코인과 이더리움 가격을 비교해줘",
    "현재 포지션이 있는지 확인해줘",
    "비트코인을 0.001개 시장가로 매수해줘",
    "미체결 주문이 있으면 취소해줘",
    "모든 포지션을 청산해줘"
]
```

## ⚠️ 주의사항

-   **실제 거래소 API 사용**: 실제 돈이 들어가는 거래이므로 테스트 시 주의 필요
-   **API 키 보안**: `.env` 파일을 git에 올리지 않도록 주의 (`.gitignore`에 포함됨)
-   **소액 테스트**: 처음 사용 시 최소 단위로 테스트 권장
-   **청산 기능**: 포지션 청산 기능은 신중하게 사용

## 🔄 워크플로우

1. **MCP 서버 실행** → Bitget API를 MCP 도구로 제공
2. **LangChain 에이전트 생성** → MCP 도구들을 자동으로 로드
3. **자연어 명령** → AI가 적절한 도구를 선택하여 실행
4. **결과 반환** → 사람이 이해하기 쉬운 형태로 응답

## 📚 기술 스택

-   **Python 3.12+**
-   **FastMCP**: MCP 서버 구현
-   **LangChain**: AI 에이전트 프레임워크
-   **langchain-mcp-adapters**: MCP와 LangChain 연결
-   **aiohttp**: HTTP 클라이언트
-   **Poetry**: 의존성 관리

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

This project is licensed under the MIT License.

## 🚨 면책 조항

이 프로젝트는 교육 및 연구 목적으로 제작되었습니다. 실제 거래 시 발생하는 손실에 대해서는 책임지지 않습니다. 투자는 본인의 판단과 책임하에 진행하시기 바랍니다.
