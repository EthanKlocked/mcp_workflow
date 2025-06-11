"""
API 키 및 인증 관련 에러:

40001-40012: ACCESS_KEY, ACCESS_SIGN, ACCESS_PASSPHRASE 등 인증 관련 오류
40037-40038: API 키 존재하지 않거나 IP 화이트리스트 오류


요청 제한 및 속도 제한 관련 에러:

40010: "Request timed out"
40018: "Invalid IP"
40429: (명시적으로 없지만 HTTP 429) "Too Many Request"


파라미터 검증 오류:

40017-40021: 파라미터 검증 실패
00001: "startTime and endTime interval cannot be greater than 366 days"


계정 상태 관련 에러:

40022-40026: 계정 제한, 동결 등
40052: "Security settings have been modified for this account..."
40082: "Internal transfer error"


거래 관련 중요 오류:

40706-40708: 주문 가격 오류, 시간 오류, 중복 오류
40711-40713: 잔고 부족 및 마진 관련 오류
40720-40721: 시장 상태 오류


시스템 관련 오류:

40200: "Server upgrade, please try again later"
40844-40845: 계약 유지보수 및 제거 관련
"""

import time
import requests
import hmac
import hashlib
import base64
import json
import random
from typing import Literal, Dict, Any, Optional

class BitgetAPI:    
    SYMBOLS = Literal['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT', 'ATOMUSDT', 'AVAXUSDT', 'BNBUSDT', 
                     'DOGEUSDT', 'DOTUSDT', 'LINKUSDT', 'LTCUSDT', 'MATICUSDT', '1000SHIBUSDT', 'STXUSDT', 
                     'TRXUSDT', 'UNIUSDT', 'TONUSDT']
    SIDES = Literal['BUY', 'SELL']
    INTERVALS = Literal['1m', '3m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d']
    TYPES = Literal['MARKET', 'LIMIT']
    MARGIN_TYPES = Literal['ISOLATED', 'CROSSED']
    PRODUCT_TYPE = 'USDT-FUTURES'  # Default product type for futures
    
    def __init__(
        self,
        api_key: str,
        secret: str,
        passphrase: str,
        base_url: str = 'https://api.bitget.com',
    ):
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.base_url = base_url
        self.headers = {
            'ACCESS-KEY': api_key,
            'ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json',
            'locale': 'en-US'
        }
    
    def get_signature(self, timestamp: int, method: str, request_path: str, query_string: str = '', body: str = '') -> str:
        if query_string:
            query_params = query_string.split('&')
            sorted_params = sorted(query_params, key=lambda x: x.split('=')[0])
            query_string = '&'.join(sorted_params)        
        if query_string:
            message = f"{timestamp}{method.upper()}{request_path}?{query_string}{body}"
        else:
            message = f"{timestamp}{method.upper()}{request_path}{body}"        
        signature = base64.b64encode(
            hmac.new(
                self.secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        
        return signature
    
    def request(
        self, 
        method: Literal["get", "post", "delete"],
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        recv_window: int = 5000
    ) -> Dict[str, Any]:
        """
        API 요청 실행
        :param method: HTTP 메서드 (get, post, delete)
        :param endpoint: API 엔드포인트
        :param params: 요청 파라미터 (GET)
        :param body: 요청 본문 (POST, DELETE)
        :param max_retries: 최대 재시도 횟수
        :param recv_window: 타임스탬프 허용 오차 (밀리초)
        :return: API 응답 (JSON)
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"        
        # Sync servertime
        timestamp = int(time.time() * 1000)
        headers = self.headers.copy()
        headers['ACCESS-TIMESTAMP'] = str(timestamp)        
        query_string = ''
        if params:
            sorted_params = dict(sorted(params.items()))
            query_string = '&'.join([f"{k}={v}" for k, v in sorted_params.items()])
            if method.lower() == 'get':
                url = f"{url}?{query_string}"        
        body_str = json.dumps(body) if body else ''        
        signature = self.get_signature(
            timestamp=timestamp,
            method=method.upper(),
            request_path=f"/{endpoint.lstrip('/')}",
            query_string=query_string if method.lower() == 'get' else '',
            body=body_str if method.lower() != 'get' else ''
        )
        headers['ACCESS-SIGN'] = signature
        
        # Retry
        retries = 0
        while retries <= max_retries:
            try:
                if method.lower() == 'get':
                    response = requests.get(url, headers=headers, timeout=10)
                elif method.lower() == 'post':
                    response = requests.post(url, headers=headers, json=body, timeout=10)
                else:  # delete
                    response = requests.delete(url, headers=headers, json=body, timeout=10)                
                status_code = response.status_code                
                # Success
                if status_code == 200:
                    return response.json()                
                # Error
                response_data = {}
                try:
                    response_data = response.json()
                except:
                    response_data = {"error": response.text}                
                if status_code == 400:
                    error_code = response_data.get("code", "")
                    error_msg = response_data.get("msg", "Unknown error")                    
                    # Case : TimeStamp
                    if error_code in ["40004", "40005", "40008"]:
                        if retries < max_retries:
                            time.sleep(1)
                            timestamp = self.get_server_time()
                            retries += 1
                            continue                    
                    # Case : Invalid Params
                    if error_code.startswith("4001") or error_code.startswith("4002"):
                        return {
                            "status": "FAILED",
                            "status_code": status_code,
                            "error_code": error_code,
                            "error_msg": error_msg,
                            "response_data": response_data
                        }                    
                elif status_code == 401 or status_code == 403:
                    # Case : Authentication Failed
                    return {
                        "status": "FAILED",
                        "status_code": status_code,
                        "error": "Authentication error" if status_code == 401 else "Access denied",
                        "response_data": response_data
                    }                    
                elif status_code == 429:
                    # Case : Request Limit
                    wait_seconds = min(30, (2 ** retries)) + random.uniform(0, 1)
                    time.sleep(wait_seconds)
                    retries += 1
                    continue                    
                elif status_code >= 500:
                    # Case : Server Error
                    if retries < max_retries:
                        wait_seconds = min(30, (2 ** retries)) + random.uniform(0, 1)
                        time.sleep(wait_seconds)
                        retries += 1
                        continue         
                # Case : Other Errors       
                return {
                    "status": "FAILED",
                    "status_code": status_code,
                    "response_data": response_data
                }                    
            except requests.exceptions.RequestException as e:
                if retries >= max_retries:
                    return {"status": "FAILED", "error": f"Request error: {str(e)}"}                
                wait_seconds = min(30, (2 ** retries)) + random.uniform(0, 1)
                time.sleep(wait_seconds)
                retries += 1                
            except Exception as e:
                if retries >= max_retries:
                    return {"status": "FAILED", "error": f"Unexpected error: {str(e)}"}                
                wait_seconds = min(30, (2 ** retries)) + random.uniform(0, 1)
                time.sleep(wait_seconds)
                retries += 1        
        return {"status": "FAILED", "error": "Max retries exceeded"}
    
    def get_server_time(self) -> int:
        try:
            response = self.request(method="get", endpoint="api/v2/public/time")
            if "data" in response and "serverTime" in response["data"]:
                return int(response["data"]["serverTime"])
        except Exception:
            pass
        return int(time.time() * 1000)
    
    def get_account_info(self, product_type: str = None) -> Dict[str, Any]:
        method = "get"
        endpoint = "api/v2/mix/account/accounts"
        params = {"productType": product_type or self.PRODUCT_TYPE}        
        return self.request(method=method, endpoint=endpoint, params=params)
    
    def get_all_positions(self, margin_coin: str = None):
        method = "get"
        endpoint = "api/v2/mix/position/all-position"        
        params = {"productType": self.PRODUCT_TYPE}        
        if margin_coin:
            params["marginCoin"] = margin_coin.upper()        
        return self.request(method=method, endpoint=endpoint, params=params)    
    
    def post_order(
        self, 
        symbol: SYMBOLS, 
        side: SIDES, 
        quantity: str, 
        _type: TYPES = "MARKET", 
        price: str = None, 
        reduce_only: bool = False, 
        time_in_force: str = "gtc",
        margin_mode: str = "isolated",
        margin_coin: str = "USDT",
        trade_side: str = None,
        client_oid: str = None,
        take_profit: str = None,
        stop_loss: str = None
    ):
        """
        선물 주문 생성
        :param symbol: 거래 심볼 (예: BTCUSDT)
        :param side: 주문 방향 (BUY 또는 SELL)
        :param quantity: 주문 수량 (문자열로 제공)
        :param _type: 주문 타입 (MARKET 또는 LIMIT)
        :param price: 지정가 주문 시 가격 (문자열로 제공)
        :param reduce_only: 포지션 감소만 허용 여부
        :param time_in_force: 주문 유효 기간 (gtc, ioc, fok, post_only)
        :param margin_mode: 마진 모드 (isolated 또는 crossed)
        :param margin_coin: 마진 코인 (예: USDT)
        :param trade_side: 거래 타입 (open 또는 close, hedge 모드에서만 필요)
        :param client_oid: 사용자 지정 주문 ID
        :param take_profit: 이익 실현 가격
        :param stop_loss: 손실 제한 가격
        :return: 주문 결과
        """
        method = "post"
        endpoint = "api/v2/mix/order/place-order"        
        order_data = {
            "symbol": symbol.lower(),
            "productType": self.PRODUCT_TYPE,
            "marginMode": margin_mode,
            "marginCoin": margin_coin.upper(),
            "size": quantity,
            "side": side.lower(),
            "orderType": _type.lower()
        }        
        # Case : Hedge Mode
        if trade_side:
            order_data["tradeSide"] = trade_side
        # Case : One-Way Mode
        if reduce_only:
            order_data["reduceOnly"] = "YES"                    
        # Case : Limit Order
        if _type.lower() == "limit":
            if not price:
                raise ValueError("Price must be provided for limit orders")
            order_data["price"] = price
            order_data["force"] = time_in_force        
        # Private Order ID
        if client_oid:
            order_data["clientOid"] = client_oid        
        # Stop Loss
        if take_profit:
            order_data["presetStopSurplusPrice"] = take_profit
        if stop_loss:
            order_data["presetStopLossPrice"] = stop_loss        
        return self.request(method=method, endpoint=endpoint, body=order_data)    
    
    def delete_order(
        self, 
        symbol: SYMBOLS, 
        order_id: str = None, 
        client_oid: str = None,
        margin_coin: str = "USDT"
    ):
        """
        선물 주문 취소
        :param symbol: 거래 심볼 (예: BTCUSDT)
        :param order_id: 주문 ID (order_id 또는 client_oid 중 하나 필수)
        :param client_oid: 클라이언트 주문 ID (order_id 또는 client_oid 중 하나 필수)
        :param margin_coin: 마진 코인 (예: USDT)
        :return: 취소 결과
        """
        if not order_id and not client_oid:
            raise ValueError("Either order_id or client_oid must be provided")        
        method = "post"
        endpoint = "api/v2/mix/order/cancel-order"
        body = {
            "symbol": symbol.lower(),
            "productType": self.PRODUCT_TYPE,
            "marginCoin": margin_coin.upper()
        }        
        if order_id:
            body["orderId"] = order_id
        if client_oid:
            body["clientOid"] = client_oid        
        return self.request(method=method, endpoint=endpoint, body=body)    
    
    def get_open_orders(
        self,
        symbol: SYMBOLS = None,
        order_id: str = None,
        client_oid: str = None,
        status: str = None,
        start_time: int = None,
        end_time: int = None,
        limit: int = 100
    ):
        """
        미체결 주문 목록 조회
        :param symbol: 거래 심볼 (예: BTCUSDT, 선택적)
        :param order_id: 주문 ID (선택적)
        :param client_oid: 클라이언트 주문 ID (선택적)
        :param status: 주문 상태 (live: 대기 중, partially_filled: 부분 체결, 선택적)
        :param start_time: 시작 시간 (밀리초 타임스탬프, 선택적)
        :param end_time: 종료 시간 (밀리초 타임스탬프, 선택적)
        :param limit: 조회할 주문 수 (최대 100, 기본값 100)
        :return: 미체결 주문 목록
        """
        method = "get"
        endpoint = "api/v2/mix/order/orders-pending"        
        params = {"productType": self.PRODUCT_TYPE}
        if symbol:
            params["symbol"] = symbol.lower()
        if order_id:
            params["orderId"] = order_id
        if client_oid:
            params["clientOid"] = client_oid
        if status:
            params["status"] = status
        if start_time:
            params["startTime"] = str(start_time)
        if end_time:
            params["endTime"] = str(end_time)
        if limit:
            params["limit"] = str(limit)        
        return self.request(method=method, endpoint=endpoint, params=params)    
    
    def set_leverage(
        self,
        symbol: SYMBOLS,
        leverage: str,
        margin_coin: str = "USDT",
        hold_side: str = None
    ):
        """
        레버리지 설정
        :param symbol: 거래 심볼 (예: BTCUSDT)
        :param leverage: 설정할 레버리지 값 (문자열로 제공)
        :param margin_coin: 마진 코인 (예: USDT)
        :param hold_side: 포지션 방향 (long: 롱 포지션, short: 숏 포지션)
            - 교차 마진(crossed)에서는 필요하지 않음
            - 격리 마진(isolated)에서:
                - 단방향 모드(one_way_mode)에서는 필요하지 않음
                - 헤지 모드(hedge_mode)에서는 필수
        :return: 레버리지 설정 결과
        """
        method = "post"
        endpoint = "api/v2/mix/account/set-leverage"
        body = {
            "symbol": symbol.lower(),
            "productType": self.PRODUCT_TYPE,
            "marginCoin": margin_coin.upper(),
            "leverage": leverage
        }
        if hold_side:
            body["holdSide"] = hold_side.lower()        
        return self.request(method=method, endpoint=endpoint, body=body)    
    
    def adjust_position_margin(
        self,
        symbol: SYMBOLS,
        amount: str,
        hold_side: str,
        margin_coin: str = "USDT"
    ):
        """
        포지션 마진 조정 (격리 마진 모드에서만 사용 가능)
        :param symbol: 거래 심볼 (예: BTCUSDT)
        :param amount: 조정할 마진 금액 (양수: 마진 추가, 음수: 마진 감소)
        :param hold_side: 포지션 방향 (long: 롱 포지션, short: 숏 포지션)
        :param margin_coin: 마진 코인 (예: USDT)
        :return: 마진 조정 결과
        """
        method = "post"
        endpoint = "api/v2/mix/account/set-margin"        
        body = {
            "symbol": symbol.lower(),
            "productType": self.PRODUCT_TYPE,
            "marginCoin": margin_coin.upper(),
            "amount": amount,
            "holdSide": hold_side.lower()
        }        
        return self.request(method=method, endpoint=endpoint, body=body)    
    
    def set_margin_mode(
        self,
        symbol: SYMBOLS,
        margin_mode: str,  # "isolated" 또는 "crossed"
        margin_coin: str = "USDT"
    ):
        """
        마진 모드 설정 (포지션 또는 미체결 주문이 없을 때만 사용 가능)
        :param symbol: 거래 심볼 (예: BTCUSDT)
        :param margin_mode: 마진 모드 ("isolated" 또는 "crossed")
        :param margin_coin: 마진 코인 (예: USDT)
        :return: 마진 모드 설정 결과
        """
        method = "post"
        endpoint = "api/v2/mix/account/set-margin-mode"        
        body = {
            "symbol": symbol.lower(),
            "productType": self.PRODUCT_TYPE,
            "marginCoin": margin_coin.upper(),
            "marginMode": margin_mode
        }        
        return self.request(method=method, endpoint=endpoint, body=body)    
    
    def set_position_mode(
        self,
        pos_mode: str,  # "one_way_mode" 또는 "hedge_mode"
        product_type: str = None
    ):
        """
        포지션 모드 설정 (단방향/헤지 모드 간 전환)
        특정 상품 유형의 모든 심볼에 적용됨
        포지션이나 미체결 주문이 있을 때는 변경 불가
        
        :param pos_mode: 포지션 모드 ("one_way_mode" 또는 "hedge_mode")
        :param product_type: 상품 유형 (기본값: self.PRODUCT_TYPE)
        :return: 포지션 모드 설정 결과
        """
        method = "post"
        endpoint = "api/v2/mix/account/set-position-mode"
        
        body = {
            "productType": product_type or self.PRODUCT_TYPE,
            "posMode": pos_mode
        }        
        return self.request(method=method, endpoint=endpoint, body=body)    
    
    def get_future_prices(
        self,
        symbol: SYMBOLS,
        interval: INTERVALS,
        start_time: int = None,
        end_time: int = None,
        limit: int = 100,
        kline_type: str = "MARKET"
    ):
        """
        선물 가격 이력(캔들스틱) 조회
        :param symbol: 거래 심볼 (예: BTCUSDT)
        :param interval: 시간 간격 (1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 12h, 1d, ...)
        :param start_time: 시작 시간 (밀리초 타임스탬프, 선택적)
        :param end_time: 종료 시간 (밀리초 타임스탬프, 선택적)
        :param limit: 조회할 캔들 수 (최대 1000, 기본값 100)
        :param kline_type: 캔들스틱 차트 타입 (MARKET, MARK, INDEX, 기본값 MARKET)
        :return: 캔들스틱 데이터
        """
        method = "get"
        endpoint = "api/v2/mix/market/candles"
        interval_mapping = {
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H",
            "1d": "1D", "3d": "3D", "1w": "1W", "1M": "1M"
        }
        bitget_interval = interval_mapping.get(interval.lower(), interval)
        params = {
            "symbol": symbol.lower(),
            "productType": self.PRODUCT_TYPE,
            "granularity": bitget_interval,
            "limit": str(limit)
        }
        if kline_type:
            params["kLineType"] = kline_type
        if start_time:
            params["startTime"] = str(start_time)
        if end_time:
            params["endTime"] = str(end_time)
        return self.request(method=method, endpoint=endpoint, params=params)    
    
    def get_future_price(
        self,
        symbol: SYMBOLS
    ):
        """
        특정 심볼의 현재 가격 정보 조회
        :param symbol: 거래 심볼 (예: BTCUSDT)
        :return: 시장 가격, 인덱스 가격, 마크 가격 정보
        """
        method = "get"
        endpoint = "api/v2/mix/market/symbol-price"        
        params = {
            "symbol": symbol.lower(),
            "productType": self.PRODUCT_TYPE
        }        
        return self.request(method=method, endpoint=endpoint, params=params)    
    
    def get_order_history(
        self,
        symbol: SYMBOLS = None,
        order_id: str = None,
        client_oid: str = None,
        order_source: str = None,
        start_time: int = None,
        end_time: int = None,
        limit: int = 100,
        id_less_than: str = None
    ):
        """
        거래 내역 조회 (최대 90일 이내)
        :param symbol: 거래 심볼 (예: BTCUSDT, 선택적)
        :param order_id: 주문 ID (선택적)
        :param client_oid: 클라이언트 주문 ID (선택적)
        :param order_source: 주문 소스 (normal, market, profit_market 등, 선택적)
        :param start_time: 시작 시간 (밀리초 타임스탬프, 선택적)
        :param end_time: 종료 시간 (밀리초 타임스탬프, 선택적)
        :param limit: 조회할 주문 수 (최대 100, 기본값 100)
        :param id_less_than: 이 ID 이전 페이지 내용 요청 (더 오래된 데이터)
        :return: 거래 내역 데이터
        """
        method = "get"
        endpoint = "api/v2/mix/order/orders-history"        
        params = {
            "productType": self.PRODUCT_TYPE,
            "limit": str(limit)
        }    
        if symbol:
            params["symbol"] = symbol.lower()        
        if order_id:
            params["orderId"] = order_id        
        if client_oid:
            params["clientOid"] = client_oid        
        if order_source:
            params["orderSource"] = order_source        
        if start_time:
            params["startTime"] = str(start_time)        
        if end_time:
            params["endTime"] = str(end_time)        
        if id_less_than:
            params["idLessThan"] = id_less_than        
        return self.request(method=method, endpoint=endpoint, params=params)    
    
    def get_exchange_info(self, symbol: SYMBOLS = None):
        """
        선물 계약 정보 조회
        :param symbol: 거래 심볼 (예: BTCUSDT, 선택적)
        :return: 계약 구성 정보
        """
        method = "get"
        endpoint = "api/v2/mix/market/contracts"
        params = {
            "productType": self.PRODUCT_TYPE
        }        
        if symbol:
            params["symbol"] = symbol.lower()        
        return self.request(method=method, endpoint=endpoint, params=params)    
    
    def get_spot_account_info(self):
        """
        현물 계정 정보 조회 (SPOT read 또는 SPOT read/write 권한 필요)
        사용자 ID, 초대자 ID, IP 화이트리스트, 권한 정보, 등록 시간 등을 포함
        
        :return: 계정 정보 데이터
            - userId: 사용자 ID
            - inviterId: 초대자 사용자 ID  
            - channelCode: 제휴 추천 코드
            - channel: 제휴
            - ips: IP 화이트리스트
            - authorities: 권한 목록 (readonly, trade 등)
            - parentId: 메인 계정 사용자 ID
            - traderType: trader 또는 not_trader
            - regisTime: 등록 시간
        """
        method = "get"
        endpoint = "api/v2/spot/account/info"
        
        return self.request(method=method, endpoint=endpoint)
    
    def get_transfer_records(
        self,
        coin: str,
        from_type: str = None,
        start_time: int = None,
        end_time: int = None,
        client_oid: str = None,
        page_num: int = 1,
        limit: int = 100,
        id_less_than: str = None
    ):
        """
        계정 간 이체 이력 조회 (최대 90일 이내)
        :param coin: 토큰 이름 (예: USDT, BTC 등) - 필수
        :param from_type: 송금 계정 타입 (선택적)
            - spot: 현물 계정
            - p2p: P2P/펀딩 계정
            - coin_futures: 코인 선물 계정
            - usdt_futures: USDT 선물 계정
            - usdc_futures: USDC 선물 계정
            - crossed_margin: 교차 마진 계정
            - isolated_margin: 격리 마진 계정
        :param start_time: 시작 시간 (밀리초 타임스탬프, 선택적)
        :param end_time: 종료 시간 (밀리초 타임스탬프, 선택적)
            - start_time과 end_time 간격은 90일을 초과할 수 없음
        :param client_oid: 사용자 지정 주문 ID (선택적)
        :param page_num: 페이지 번호 (기본값: 1, 최대: 1000)
        :param limit: 반환할 결과 수 (기본값: 100, 최대: 500)
        :param id_less_than: 이 ID 이전 페이지 내용 요청 (더 오래된 데이터, 비추천)
        :return: 이체 이력 데이터
            - coin: 토큰 이름
            - status: 이체 상태 (Successful, Failed, Processing)
            - toType: 수취 계정 타입
            - toSymbol: 수취 계정 거래쌍 (격리 마진인 경우)
            - fromType: 송금 계정 타입
            - fromSymbol: 송금 계정 거래쌍 (격리 마진인 경우)
            - size: 이체 수량
            - ts: 이체 시간 (밀리초 타임스탬프)
            - clientOid: 사용자 지정 주문 ID
            - transferId: 이체 주문 ID
        """
        method = "get"
        endpoint = "api/v2/spot/account/transferRecords"        
        params = {
            "coin": coin.upper(),
            "pageNum": str(page_num),
            "limit": str(limit)
        }        
        if from_type:
            params["fromType"] = from_type
        if start_time:
            params["startTime"] = str(start_time)
        if end_time:
            params["endTime"] = str(end_time)
        if client_oid:
            params["clientOid"] = client_oid
        if id_less_than:
            params["idLessThan"] = id_less_than
        
        return self.request(method=method, endpoint=endpoint, params=params)    
    
    def get_withdrawal_records(
        self,
        coin: str = None,
        client_oid: str = None,
        start_time: int = None,
        end_time: int = None,
        id_less_than: str = None,
        order_id: str = None,
        limit: int = 20
    ):
        """
        출금 이력 조회
        :param coin: 코인 이름 (예: USDT, BTC 등, 선택적)
        :param client_oid: 클라이언트 사용자 지정 ID (선택적)
        :param start_time: 조회 시작 시간 (밀리초 타임스탬프) - 필수
        :param end_time: 조회 종료 시간 (밀리초 타임스탬프) - 필수
        :param id_less_than: 이 ID 이전 페이지 내용 요청 (더 오래된 데이터, 선택적)
        :param order_id: 응답에서 받은 주문 ID (선택적)
        :param limit: 페이지당 항목 수 (기본값: 20, 최대: 100)
        :return: 출금 이력 데이터
            - orderId: 주문 ID
            - tradeId: 거래 ID (온체인: 해시값, 내부이체: 거래ID)
            - coin: 토큰 이름
            - dest: 출금 타입 (on_chain: 온체인 출금, internal_transfer: 내부 이체)
            - clientOid: 클라이언트 사용자 지정 ID
            - type: 타입 (고정값: withdraw)
            - size: 출금 수량
            - fee: 거래 수수료
            - status: 출금 상태 (pending: 검토 대기, fail: 실패, success: 성공)
            - fromAddress: 출금 시작 주소 (온체인: 주소, 내부이체: UID/이메일/전화번호)
            - toAddress: 수취 주소 (온체인: 주소, 내부이체: UID/이메일/전화번호)
            - chain: 출금 네트워크 (내부이체인 경우 무시)
            - confirm: 확인된 블록 수
            - tag: 태그
            - cTime: 생성 시간 (밀리초)
            - uTime: 업데이트 시간 (밀리초)
        """
        method = "get"
        endpoint = "api/v2/spot/wallet/withdrawal-records"        
        params = {
            "limit": str(limit)
        }        
        if coin:
            params["coin"] = coin.upper()
        if client_oid:
            params["clientOid"] = client_oid
        if start_time:
            params["startTime"] = str(start_time)
        if end_time:
            params["endTime"] = str(end_time)
        if id_less_than:
            params["idLessThan"] = id_less_than
        if order_id:
            params["orderId"] = order_id        
        return self.request(method=method, endpoint=endpoint, params=params)    
    
    def get_deposit_records(
        self,
        coin: str = None,
        order_id: str = None,
        start_time: int = None,
        end_time: int = None,
        id_less_than: str = None,
        limit: int = 20
    ):
        """
        입금 이력 조회
        :param coin: 코인 이름 (예: USDT, BTC 등, 선택적)
        :param order_id: 응답에서 받은 주문 ID (선택적)
        :param start_time: 조회 시작 시간 (밀리초 타임스탬프) - 필수
        :param end_time: 조회 종료 시간 (밀리초 타임스탬프) - 필수
        :param id_less_than: 이 ID 이전 페이지 내용 요청 (더 오래된 데이터, 선택적)
        :param limit: 페이지당 항목 수 (기본값: 20, 최대: 100)
        :return: 입금 이력 데이터
            - orderId: 주문 ID
            - tradeId: 거래 ID (온체인: 해시값, 내부이체: 거래ID)
            - coin: 토큰 이름
            - type: 타입 (고정값: deposit)
            - size: 입금 수량
            - status: 입금 상태 (pending: 확인 대기, fail: 실패, success: 성공)
            - fromAddress: 입금 발송 주소 (온체인: 주소, 내부이체: UID/이메일/전화번호)
            - toAddress: 입금 수취 주소 (온체인: 주소, 내부이체: UID/이메일/전화번호)
            - chain: 입금 네트워크 (내부이체인 경우 무시)
            - dest: 입금 타입 (on_chain: 온체인 입금, internal_transfer: 내부 입금)
            - cTime: 생성 시간 (밀리초)
            - uTime: 업데이트 시간 (밀리초)
        """
        method = "get"
        endpoint = "api/v2/spot/wallet/deposit-records"        
        params = {
            "limit": str(limit)
        }        
        if coin:
            params["coin"] = coin.upper()
        if order_id:
            params["orderId"] = order_id
        if start_time:
            params["startTime"] = str(start_time)
        if end_time:
            params["endTime"] = str(end_time)
        if id_less_than:
            params["idLessThan"] = id_less_than        
        return self.request(method=method, endpoint=endpoint, params=params)    