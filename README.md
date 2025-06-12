# AI Workflow with MCP

MCP(Model Context Protocol) 서버와 클라이언트를 활용한 AI 에이전트 워크플로우 시스템

## 🚀 주요 기능

-   **MCP 서버**: 다양한 도구들을 MCP 프로토콜로 제공
-   **LangChain 에이전트**: MCP 도구를 활용한 AI 에이전트
-   **암호화폐 거래**: Bitget API를 통한 실시간 거래
-   **기술적 분석**: RSI, 이동평균, 볼린저밴드 등 차트 분석
-   **뉴스 분석**: 무료 소스를 통한 암호화폐 뉴스 수집 및 감정 분석
-   **워크플로우 자동화**: AI 에이전트 기반 투자 전략 실행

## 📁 프로젝트 구조

```
ai_workflow/
├── src/
│   ├── ability/module/
│   │   └── bitget_trader.py          # Bitget API 클라이언트
│   ├── core/
│   │   ├── mcp_client.py             # MCP 클라이언트 (HTTP 기반)
│   │   ├── mcp_server.py             # MCP 서버 (통합 도구 제공)
│   │   ├── langchain_agent.py        # LangChain 에이전트
│   │   └── mcp_tools/
│   │       ├── bitget_tools.py       # Bitget 거래 도구들
│   │       ├── technical_analysis_tools.py  # 기술적 분석 도구들
│   │       └── crypto_news_tools.py  # 암호화폐 뉴스 도구들
│   ├── operator/trader/
│   │   ├── bitget_trade_workflow.py  # 거래 워크플로우
│   │   └── role/                     # 에이전트 역할 정의
│   └── test/
│       └── test.ipynb                # 테스트 노트북
├── pyproject.toml                    # Poetry 설정
├── .env.example                      # 환경변수 템플릿
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

# AI 모델 설정
AI_MODEL=gpt4mini  # 또는 gpt4, claude3s
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Bitget API 설정 (거래 기능 사용 시)
BITGET_API_KEY=your_bitget_api_key
BITGET_SECRET_KEY=your_bitget_secret_key
BITGET_PASSPHRASE=your_bitget_passphrase
```

### 3. MCP 서버 실행

```bash
# MCP 서버 시작
cd src/core
python mcp_server.py
```

서버 실행 후 다음과 같은 메시지가 표시됩니다:

```
🔧 Bitget 거래 도구 등록 완료
📊 기술적 분석 도구 등록 완료
🆓 무료 암호화폐 뉴스 도구 등록 완료
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
    agent_client = LangChainAgent(model_key="gpt4")

    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 에이전트 생성
            agent = await agent_client.create_agent(session, "trading_agent")

            # 다양한 기능 테스트
            questions = [
                "비트코인 현재 가격을 알려줘",
                "비트코인의 RSI를 분석해줘",
                "최신 암호화폐 뉴스를 감정 분석해줘",
                "이더리움 기술적 분석 종합 보고서를 작성해줘"
            ]

            for question in questions:
                answer = await agent_client.ask_agent(question, "trading_agent")
                print(f"Q: {question}")
                print(f"A: {answer}\n")

await test_agent()
```

## 🔧 주요 MCP 도구들

### 📈 Bitget 거래 도구 (bitget_tools.py)

#### 계정 및 포지션 관리

-   `get_bitget_account_info()` - 계정 잔고 및 정보 조회
-   `get_bitget_positions()` - 현재 포지션 목록 조회
-   `show_position_details()` - 포지션 상세 정보 조회

#### 시장 데이터

-   `get_bitget_price(symbol)` - 특정 코인 현재 가격 조회
-   `get_bitget_candles(symbol, interval, limit)` - 캔들스틱 차트 데이터

#### 주문 관리

-   `place_bitget_order(symbol, side, quantity, type, price)` - 주문 생성
-   `cancel_bitget_order(symbol, order_id)` - 주문 취소
-   `get_bitget_open_orders(symbol)` - 미체결 주문 조회
-   `get_bitget_order_history(symbol, limit)` - 거래 내역 조회

#### 포지션 청산

-   `close_bitget_position_correct(symbol)` - 특정 포지션 청산
-   `close_all_bitget_positions_correct()` - 모든 포지션 청산

#### 계정 설정

-   `set_bitget_leverage(symbol, leverage)` - 레버리지 설정
-   `get_bitget_leverage_info(symbol)` - 레버리지 정보 조회

### 📊 기술적 분석 도구 (technical_analysis_tools.py)

#### 개별 지표 분석

-   `analyze_rsi(symbol, period, interval)` - RSI 과매수/과매도 분석
-   `analyze_moving_averages(symbol, short_ma, long_ma, interval)` - 이동평균선 및 골든크로스/데드크로스 분석
-   `analyze_bollinger_bands(symbol, period, std_dev, interval)` - 볼린저밴드 변동성 분석

#### 종합 분석

-   `comprehensive_technical_analysis(symbol, interval)` - RSI, 이동평균, 볼린저밴드 통합 분석 및 투자 신호 생성

### 📰 암호화폐 뉴스 도구 (crypto_news_tools.py)

#### 뉴스 수집

-   `get_latest_crypto_news(sources, limit_per_source)` - 다양한 무료 소스에서 최신 뉴스 수집
-   `get_trending_crypto_info()` - CoinGecko 트렌딩 코인 정보 및 관련 뉴스
-   `monitor_breaking_news(keywords)` - 키워드 기반 속보 모니터링

#### 지원하는 뉴스 소스

-   **RSS 피드**: CoinDesk, CoinTelegraph, Bitcoinist, Decrypt, CryptoSlate, CryptoPotato, CryptoNews, NewsBTC
-   **API**: CryptoCompare, CoinGecko
-   **기능**: 감정 분석, 코인 언급 추출, 트렌드 분석

## 💡 사용 예시

### 거래 관련 질문

```python
trading_questions = [
    "현재 계정 잔고를 확인해줘",
    "비트코인과 이더리움 가격을 비교해줘",
    "현재 포지션이 있는지 확인해줘",
    "비트코인을 0.001개 시장가로 매수해줘",
    "모든 포지션을 청산해줘"
]
```

### 기술적 분석 질문

```python
analysis_questions = [
    "비트코인의 RSI를 분석해줘",
    "이더리움의 이동평균선 분석을 해줘",
    "솔라나의 볼린저밴드 상태를 확인해줘",
    "리플에 대한 종합 기술적 분석을 해줘"
]
```

### 뉴스 및 시장 분석 질문

```python
news_questions = [
    "최신 암호화폐 뉴스를 감정 분석해줘",
    "비트코인 관련 속보가 있는지 확인해줘",
    "트렌딩 코인 정보를 알려줘",
    "최근 3시간 동안의 핫한 뉴스를 분석해줘"
]
```

### 종합 투자 분석 질문

```python
comprehensive_questions = [
    "비트코인 기술적 분석과 뉴스 분석을 종합해서 투자 추천해줘",
    "현재 시장 상황을 종합적으로 분석해줘",
    "포트폴리오 리밸런싱 추천해줘"
]
```

## 🎯 워크플로우 예시

### 1. 기본 투자 분석 워크플로우

1. **뉴스 수집** → 시장 감정 파악
2. **기술적 분석** → 차트 패턴 및 지표 분석
3. **종합 판단** → AI가 투자 신호 생성
4. **리스크 관리** → 손절매 및 목표가 제시

### 2. 자동 거래 워크플로우

1. **시장 모니터링** → 실시간 가격 및 뉴스 추적
2. **신호 감지** → 기술적 분석 기반 매매 신호
3. **자동 주문** → 사전 설정된 전략에 따른 주문 실행
4. **포지션 관리** → 손익 추적 및 청산 관리

## ⚠️ 주의사항

-   **실제 거래소 API 사용**: 실제 돈이 들어가는 거래이므로 테스트 시 주의 필요
-   **API 키 보안**: `.env` 파일을 git에 올리지 않도록 주의 (`.gitignore`에 포함됨)
-   **소액 테스트**: 처음 사용 시 최소 단위로 테스트 권장
-   **투자 책임**: AI 분석은 참고용이며, 최종 투자 결정은 본인 책임
-   **리스크 관리**: 항상 손절매를 설정하고 과도한 레버리지 지양

## 🔄 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   사용자 질문    │───▶│  LangChain      │───▶│   MCP 서버      │
│   (자연어)      │    │  에이전트       │    │   (도구 제공)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │                       │
                               ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  도구 선택 및   │    │  Bitget API     │
                       │  실행 계획      │    │  뉴스 API       │
                       └─────────────────┘    │  기술적 분석    │
                               │              └─────────────────┘
                               ▼
                       ┌─────────────────┐
                       │   결과 통합 및  │
                       │   자연어 응답   │
                       └─────────────────┘
```

## 📚 기술 스택

### 핵심 프레임워크

-   **Python 3.12+**
-   **FastMCP**: MCP 서버 구현
-   **LangChain**: AI 에이전트 프레임워크
-   **langchain-mcp-adapters**: MCP와 LangChain 연결

### 데이터 처리

-   **pandas**: 시계열 데이터 분석
-   **numpy**: 수치 계산
-   **feedparser**: RSS 피드 파싱
-   **requests**: HTTP API 호출

### 통신 및 인프라

-   **aiohttp**: 비동기 HTTP 클라이언트
-   **Poetry**: 의존성 관리
-   **python-dotenv**: 환경변수 관리

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📈 향후 계획

-   [ ] 더 많은 거래소 지원 (바이낸스, 업비트 등)
-   [ ] 고급 기술적 지표 추가 (MACD, 피보나치 등)
-   [ ] 백테스팅 기능 구현
-   [ ] 웹 대시보드 개발
-   [ ] 알림 시스템 구축 (텔레그램, 이메일)
-   [ ] 포트폴리오 최적화 알고리즘

## 🚨 면책 조항

이 프로젝트는 교육 및 연구 목적으로 제작되었습니다.

-   **투자 책임**: 모든 투자 결정과 그에 따른 손실은 사용자 본인의 책임입니다.
-   **AI 한계**: AI 분석은 참고용이며, 100% 정확성을 보장하지 않습니다.
-   **시장 리스크**: 암호화폐 시장은 높은 변동성을 가지므로 신중한 투자가 필요합니다.
-   **기술적 리스크**: 소프트웨어 버그나 API 오류로 인한 손실 가능성이 있습니다.

**투자 전 반드시 충분한 학습과 리스크 관리 계획을 수립하시기 바랍니다.**
