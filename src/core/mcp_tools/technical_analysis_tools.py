import json
import pandas as pd
import numpy as np
from typing import List, Dict
from ability.module.bitget_trader import BitgetAPI  
import os

def register_technical_analysis_tools(mcp):    
    
    def get_bitget_client():
        api_key = os.getenv("BITGET_API_KEY")
        secret_key = os.getenv("BITGET_SECRET_KEY")
        passphrase = os.getenv("BITGET_PASSPHRASE")    
        if not all([api_key, secret_key, passphrase]):
            raise ValueError("Bitget API credentials not found in environment variables")    
        return BitgetAPI(
            api_key=api_key,
            secret=secret_key,
            passphrase=passphrase
        )
            
    def get_candle_data(symbol: str, interval: str = "1h", limit: int = 100) -> pd.DataFrame:
        """캔들 데이터를 DataFrame으로 변환"""
        try:
            client = get_bitget_client()
            candles_response = client.get_future_prices(
                symbol=symbol.upper(),
                interval=interval,
                limit=limit
            )
            
            if candles_response.get("code") != "00000":
                raise Exception(f"Failed to get candles: {candles_response}")
            
            candles_data = candles_response.get("data", [])
            
            # DataFrame 생성 (실제 API 응답: [timestamp, open, high, low, close, volume, baseVolume])
            df = pd.DataFrame(candles_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'base_volume'
            ])
            
            # base_volume은 사용하지 않으므로 제거
            df = df.drop('base_volume', axis=1)
            
            # 데이터 타입 변환
            df['timestamp'] = pd.to_numeric(df['timestamp'])
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # 타임스탬프를 datetime으로 변환
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp').reset_index(drop=True)        
            
            return df
            
        except Exception as e:
            print(f"Error details: {str(e)}")
            raise Exception(f"Error getting candle data: {str(e)}")
    
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_moving_average(prices: pd.Series, period: int) -> pd.Series:
        """이동평균선 계산"""
        return prices.rolling(window=period).mean()
    
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2):
        """볼린저 밴드 계산"""
        ma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = ma + (std * std_dev)
        lower_band = ma - (std * std_dev)
        return upper_band, ma, lower_band
    
    @mcp.tool()
    async def analyze_rsi(symbol: str, period: int = 14, interval: str = "1h") -> str:
        """
        RSI 분석 - 과매수/과매도 상태 판단
        
        Args:
            symbol: 거래 심볼 (e.g., BTCUSDT)
            period: RSI 계산 기간 (기본값: 14)
            interval: 시간 간격 (1h, 4h, 1d 등)
        """
        try:
            df = get_candle_data(symbol, interval, 100)
            
            if df.empty or len(df) < period + 1:
                return json.dumps({"error": "충분한 데이터가 없습니다"}, ensure_ascii=False, indent=2)
            
            rsi = calculate_rsi(df['close'], period)
            
            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else current_rsi
            
            # RSI 해석
            if pd.isna(current_rsi):
                return json.dumps({"error": "RSI 계산 불가"}, ensure_ascii=False, indent=2)
            
            if current_rsi >= 70:
                signal = "과매수 - 매도 고려"
                strength = "강함" if current_rsi >= 80 else "보통"
            elif current_rsi <= 30:
                signal = "과매도 - 매수 고려"  
                strength = "강함" if current_rsi <= 20 else "보통"
            else:
                signal = "중립"
                strength = "중립"
            
            # 추세 분석
            trend = "상승" if current_rsi > prev_rsi else "하락"
            
            result = {
                "symbol": symbol,
                "interval": interval,
                "current_rsi": round(float(current_rsi), 2),
                "previous_rsi": round(float(prev_rsi), 2),
                "signal": signal,
                "strength": strength,
                "trend": trend,
                "analysis": {
                    "oversold_threshold": 30,
                    "overbought_threshold": 70,
                    "current_price": float(df['close'].iloc[-1]),
                    "timestamp": df['datetime'].iloc[-1].isoformat()
                }
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def analyze_moving_averages(symbol: str, short_ma: int = 20, long_ma: int = 50, interval: str = "1h") -> str:
        """
        이동평균선 분석 및 골든크로스/데드크로스 감지
        
        Args:
            symbol: 거래 심볼 (e.g., BTCUSDT)
            short_ma: 단기 이동평균 기간 (기본값: 20)
            long_ma: 장기 이동평균 기간 (기본값: 50)
            interval: 시간 간격
        """
        try:
            df = get_candle_data(symbol, interval, max(long_ma + 20, 100))
            
            if df.empty or len(df) < long_ma + 1:
                return json.dumps({"error": "충분한 데이터가 없습니다"}, ensure_ascii=False, indent=2)
            
            # 이동평균선 계산
            df[f'ma_{short_ma}'] = calculate_moving_average(df['close'], short_ma)
            df[f'ma_{long_ma}'] = calculate_moving_average(df['close'], long_ma)
            
            current_short_ma = df[f'ma_{short_ma}'].iloc[-1]
            current_long_ma = df[f'ma_{long_ma}'].iloc[-1]
            prev_short_ma = df[f'ma_{short_ma}'].iloc[-2] if len(df) > 1 else current_short_ma
            prev_long_ma = df[f'ma_{long_ma}'].iloc[-2] if len(df) > 1 else current_long_ma
            current_price = df['close'].iloc[-1]
            
            # NaN 체크
            if pd.isna(current_short_ma) or pd.isna(current_long_ma):
                return json.dumps({"error": "이동평균 계산 불가"}, ensure_ascii=False, indent=2)
            
            # 크로스 감지
            cross_signal = "없음"
            if not pd.isna(prev_short_ma) and not pd.isna(prev_long_ma):
                if prev_short_ma <= prev_long_ma and current_short_ma > current_long_ma:
                    cross_signal = "골든크로스 - 강한 매수 신호"
                elif prev_short_ma >= prev_long_ma and current_short_ma < current_long_ma:
                    cross_signal = "데드크로스 - 강한 매도 신호"
            
            # 가격 대비 이동평균 위치
            price_vs_ma = []
            if current_price > current_short_ma:
                price_vs_ma.append(f"가격이 {short_ma}일선 위에 있음 (상승 추세)")
            else:
                price_vs_ma.append(f"가격이 {short_ma}일선 아래에 있음 (하락 추세)")
            
            if current_price > current_long_ma:
                price_vs_ma.append(f"가격이 {long_ma}일선 위에 있음 (장기 상승)")
            else:
                price_vs_ma.append(f"가격이 {long_ma}일선 아래에 있음 (장기 하락)")
            
            result = {
                "symbol": symbol,
                "interval": interval,
                "current_price": round(float(current_price), 4),
                "moving_averages": {
                    f"ma_{short_ma}": round(float(current_short_ma), 4),
                    f"ma_{long_ma}": round(float(current_long_ma), 4)
                },
                "cross_signal": cross_signal,
                "price_analysis": price_vs_ma,
                "trend_strength": {
                    "short_term": "상승" if current_short_ma > prev_short_ma else "하락",
                    "long_term": "상승" if current_long_ma > prev_long_ma else "하락"
                },
                "timestamp": df['datetime'].iloc[-1].isoformat()
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def analyze_bollinger_bands(symbol: str, period: int = 20, std_dev: int = 2, interval: str = "1h") -> str:
        """
        볼린저 밴드 분석 - 변동성 및 진입점 분석
        
        Args:
            symbol: 거래 심볼 (e.g., BTCUSDT)
            period: 볼린저 밴드 기간 (기본값: 20)
            std_dev: 표준편차 배수 (기본값: 2)
            interval: 시간 간격
        """
        try:
            df = get_candle_data(symbol, interval, max(period + 20, 100))
            
            if df.empty or len(df) < period + 1:
                return json.dumps({"error": "충분한 데이터가 없습니다"}, ensure_ascii=False, indent=2)
            
            # 볼린저 밴드 계산
            upper_band, middle_band, lower_band = calculate_bollinger_bands(df['close'], period, std_dev)
            
            current_price = df['close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_middle = middle_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            # NaN 체크
            if pd.isna(current_upper) or pd.isna(current_middle) or pd.isna(current_lower):
                return json.dumps({"error": "볼린저 밴드 계산 불가"}, ensure_ascii=False, indent=2)
            
            # 밴드폭 계산 (변동성 지표)
            band_width = ((current_upper - current_lower) / current_middle) * 100
            
            # 가격 위치 분석
            price_position = ((current_price - current_lower) / (current_upper - current_lower)) * 100
            
            # 신호 생성
            if current_price >= current_upper:
                signal = "상단 밴드 접촉 - 과매수, 매도 고려"
                strength = "강함"
            elif current_price <= current_lower:
                signal = "하단 밴드 접촉 - 과매도, 매수 고려"
                strength = "강함"
            elif current_price > current_middle:
                signal = "중간선 위 - 상승 추세"
                strength = "보통"
            else:
                signal = "중간선 아래 - 하락 추세"
                strength = "보통"
            
            # 스퀴즈 감지 (낮은 변동성)
            squeeze_threshold = 10  # 밴드폭 10% 이하면 스퀴즈
            is_squeeze = band_width < squeeze_threshold
            
            result = {
                "symbol": symbol,
                "interval": interval,
                "current_price": round(float(current_price), 4),
                "bollinger_bands": {
                    "upper_band": round(float(current_upper), 4),
                    "middle_band": round(float(current_middle), 4),
                    "lower_band": round(float(current_lower), 4)
                },
                "analysis": {
                    "signal": signal,
                    "strength": strength,
                    "price_position_percent": round(float(price_position), 1),
                    "band_width_percent": round(float(band_width), 2),
                    "is_squeeze": is_squeeze,
                    "volatility": "낮음" if band_width < 10 else "보통" if band_width < 20 else "높음"
                },
                "trading_insight": {
                    "squeeze_breakout": "변동성 돌파 대기" if is_squeeze else "정상 변동성",
                    "mean_reversion": f"중간선까지 {abs(float(current_price - current_middle)):.2f} 차이"
                },
                "timestamp": df['datetime'].iloc[-1].isoformat()
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def comprehensive_technical_analysis(symbol: str, interval: str = "1h") -> str:
        """
        종합 기술적 분석 - RSI, 이동평균, 볼린저밴드 통합 분석
        
        Args:
            symbol: 거래 심볼 (e.g., BTCUSDT)
            interval: 시간 간격
        """
        try:
            # 데이터 한 번만 가져와서 모든 분석에 사용
            df = get_candle_data(symbol, interval, 200)  # 더 많은 데이터
            
            if df.empty or len(df) < 50:
                return json.dumps({"error": "충분한 데이터가 없습니다"}, ensure_ascii=False, indent=2)
            
            # 직접 계산으로 더 안정적으로 처리
            results = {}
            total_score = 0
            signals = []
            
            # RSI 분석
            try:
                rsi = calculate_rsi(df['close'], 14)
                current_rsi = rsi.iloc[-1]
                
                if not pd.isna(current_rsi):
                    if current_rsi <= 30:
                        signals.append("RSI: 과매도 - 매수 신호")
                        total_score += 1
                        if current_rsi <= 20:
                            total_score += 1  # 강한 신호
                    elif current_rsi >= 70:
                        signals.append("RSI: 과매수 - 매도 신호")
                        total_score -= 1
                        if current_rsi >= 80:
                            total_score -= 1  # 강한 신호
                    else:
                        signals.append("RSI: 중립")
                    
                    results["rsi"] = {
                        "current": round(float(current_rsi), 2),
                        "signal": "과매도" if current_rsi <= 30 else "과매수" if current_rsi >= 70 else "중립"
                    }
                else:
                    signals.append("RSI: 계산 불가")
            except Exception as e:
                signals.append(f"RSI: 오류 ({str(e)})")
            
            # 이동평균 분석
            try:
                ma_20 = calculate_moving_average(df['close'], 20).iloc[-1]
                ma_50 = calculate_moving_average(df['close'], 50).iloc[-1]
                current_price = df['close'].iloc[-1]
                
                if not pd.isna(ma_20) and not pd.isna(ma_50):
                    # 골든크로스/데드크로스 체크
                    if len(df) > 1:
                        prev_ma_20 = calculate_moving_average(df['close'], 20).iloc[-2]
                        prev_ma_50 = calculate_moving_average(df['close'], 50).iloc[-2]
                        
                        if prev_ma_20 <= prev_ma_50 and ma_20 > ma_50:
                            signals.append("이동평균: 골든크로스 - 강한 매수")
                            total_score += 2
                        elif prev_ma_20 >= prev_ma_50 and ma_20 < ma_50:
                            signals.append("이동평균: 데드크로스 - 강한 매도")
                            total_score -= 2
                        else:
                            # 일반적인 이동평균 신호
                            if current_price > ma_20 > ma_50:
                                signals.append("이동평균: 상승 정렬")
                                total_score += 1
                            elif current_price < ma_20 < ma_50:
                                signals.append("이동평균: 하락 정렬")
                                total_score -= 1
                            else:
                                signals.append("이동평균: 혼재")
                    
                    results["moving_average"] = {
                        "ma_20": round(float(ma_20), 2),
                        "ma_50": round(float(ma_50), 2),
                        "current_price": round(float(current_price), 2),
                        "trend": "상승" if ma_20 > ma_50 else "하락"
                    }
                else:
                    signals.append("이동평균: 계산 불가")
            except Exception as e:
                signals.append(f"이동평균: 오류 ({str(e)})")
            
            # 볼린저밴드 분석
            try:
                upper_band, middle_band, lower_band = calculate_bollinger_bands(df['close'], 20, 2)
                current_upper = upper_band.iloc[-1]
                current_middle = middle_band.iloc[-1]
                current_lower = lower_band.iloc[-1]
                
                if not pd.isna(current_upper) and not pd.isna(current_lower):
                    if current_price >= current_upper:
                        signals.append("볼린저밴드: 상단 접촉 - 매도 고려")
                        total_score -= 1
                    elif current_price <= current_lower:
                        signals.append("볼린저밴드: 하단 접촉 - 매수 고려")
                        total_score += 1
                    else:
                        signals.append("볼린저밴드: 중립")
                    
                    results["bollinger_bands"] = {
                        "upper": round(float(current_upper), 2),
                        "middle": round(float(current_middle), 2),
                        "lower": round(float(current_lower), 2),
                        "position": round(((current_price - current_lower) / (current_upper - current_lower)) * 100, 1)
                    }
                else:
                    signals.append("볼린저밴드: 계산 불가")
            except Exception as e:
                signals.append(f"볼린저밴드: 오류 ({str(e)})")
            
            # 종합 판단
            if total_score >= 3:
                overall_signal = "강한 매수 추천"
                recommendation = "여러 지표가 매수 신호를 보이고 있습니다. 하지만 리스크 관리는 필수입니다."
            elif total_score >= 1:
                overall_signal = "매수 고려"
                recommendation = "일부 지표에서 매수 신호가 나타나고 있습니다. 추가 확인 후 결정하세요."
            elif total_score <= -3:
                overall_signal = "강한 매도 추천"
                recommendation = "여러 지표가 매도 신호를 보이고 있습니다. 손절 고려가 필요합니다."
            elif total_score <= -1:
                overall_signal = "매도 고려"
                recommendation = "일부 지표에서 매도 신호가 나타나고 있습니다. 주의 깊게 모니터링하세요."
            else:
                overall_signal = "중립 - 대기"
                recommendation = "명확한 신호가 없는 상태입니다. 추세 확인 후 진입하세요."
            
            comprehensive_result = {
                "symbol": symbol,
                "interval": interval,
                "timestamp": df['datetime'].iloc[-1].isoformat(),
                "current_price": round(float(df['close'].iloc[-1]), 2),
                "overall_signal": overall_signal,
                "confidence_score": f"{total_score}/6",
                "recommendation": recommendation,
                "individual_signals": signals,
                "technical_indicators": results,
                "risk_warning": "이 분석은 참고용이며, 투자 결정은 본인 책임입니다. 손절매 설정을 권장합니다."
            }
            
            return json.dumps(comprehensive_result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"종합 분석 중 오류: {str(e)}"}, ensure_ascii=False, indent=2)
    
    print("📊 수정된 기술적 분석 도구 등록 완료")