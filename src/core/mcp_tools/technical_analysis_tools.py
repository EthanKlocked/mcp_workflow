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
            
            df = pd.DataFrame(candles_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'base_volume'
            ])
            
            df = df.drop('base_volume', axis=1)
            
            df['timestamp'] = pd.to_numeric(df['timestamp'])
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp').reset_index(drop=True)        
            
            return df
            
        except Exception as e:
            print(f"Error details: {str(e)}")
            raise Exception(f"Error getting candle data: {str(e)}")
    
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_moving_average(prices: pd.Series, period: int) -> pd.Series:
        return prices.rolling(window=period).mean()
    
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2):
        ma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = ma + (std * std_dev)
        lower_band = ma - (std * std_dev)
        return upper_band, ma, lower_band
    
    @mcp.tool()
    async def analyze_rsi(symbol: str, period: int = 14, interval: str = "1h") -> str:
        """
        Analyze RSI (Relative Strength Index) to determine overbought/oversold conditions.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT, ETHUSDT)
            period: RSI calculation period (default: 14)
            interval: Time interval (1h, 4h, 1d, etc.)
        """
        try:
            df = get_candle_data(symbol, interval, 100)
            
            if df.empty or len(df) < period + 1:
                return json.dumps({"error": "Insufficient data for RSI calculation"}, ensure_ascii=False, indent=2)
            
            rsi = calculate_rsi(df['close'], period)
            
            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else current_rsi
            
            if pd.isna(current_rsi):
                return json.dumps({"error": "RSI calculation failed"}, ensure_ascii=False, indent=2)
            
            if current_rsi >= 70:
                signal = "Overbought - Consider selling"
                strength = "Strong" if current_rsi >= 80 else "Medium"
            elif current_rsi <= 30:
                signal = "Oversold - Consider buying"  
                strength = "Strong" if current_rsi <= 20 else "Medium"
            else:
                signal = "Neutral"
                strength = "Neutral"
            
            trend = "Rising" if current_rsi > prev_rsi else "Falling"
            
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
        Analyze moving averages and detect golden cross/death cross patterns.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT, ETHUSDT)
            short_ma: Short-term moving average period (default: 20)
            long_ma: Long-term moving average period (default: 50)
            interval: Time interval for analysis
        """
        try:
            df = get_candle_data(symbol, interval, max(long_ma + 20, 100))
            
            if df.empty or len(df) < long_ma + 1:
                return json.dumps({"error": "Insufficient data for moving average calculation"}, ensure_ascii=False, indent=2)
            
            df[f'ma_{short_ma}'] = calculate_moving_average(df['close'], short_ma)
            df[f'ma_{long_ma}'] = calculate_moving_average(df['close'], long_ma)
            
            current_short_ma = df[f'ma_{short_ma}'].iloc[-1]
            current_long_ma = df[f'ma_{long_ma}'].iloc[-1]
            prev_short_ma = df[f'ma_{short_ma}'].iloc[-2] if len(df) > 1 else current_short_ma
            prev_long_ma = df[f'ma_{long_ma}'].iloc[-2] if len(df) > 1 else current_long_ma
            current_price = df['close'].iloc[-1]
            
            if pd.isna(current_short_ma) or pd.isna(current_long_ma):
                return json.dumps({"error": "Moving average calculation failed"}, ensure_ascii=False, indent=2)
            
            cross_signal = "None"
            if not pd.isna(prev_short_ma) and not pd.isna(prev_long_ma):
                if prev_short_ma <= prev_long_ma and current_short_ma > current_long_ma:
                    cross_signal = "Golden Cross - Strong buy signal"
                elif prev_short_ma >= prev_long_ma and current_short_ma < current_long_ma:
                    cross_signal = "Death Cross - Strong sell signal"
            
            price_vs_ma = []
            if current_price > current_short_ma:
                price_vs_ma.append(f"Price above {short_ma}-period MA (Uptrend)")
            else:
                price_vs_ma.append(f"Price below {short_ma}-period MA (Downtrend)")
            
            if current_price > current_long_ma:
                price_vs_ma.append(f"Price above {long_ma}-period MA (Long-term uptrend)")
            else:
                price_vs_ma.append(f"Price below {long_ma}-period MA (Long-term downtrend)")
            
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
                    "short_term": "Rising" if current_short_ma > prev_short_ma else "Falling",
                    "long_term": "Rising" if current_long_ma > prev_long_ma else "Falling"
                },
                "timestamp": df['datetime'].iloc[-1].isoformat()
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def analyze_bollinger_bands(symbol: str, period: int = 20, std_dev: int = 2, interval: str = "1h") -> str:
        """
        Analyze Bollinger Bands for volatility and entry point identification.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT, ETHUSDT)
            period: Bollinger Bands period (default: 20)
            std_dev: Standard deviation multiplier (default: 2)
            interval: Time interval for analysis
        """
        try:
            df = get_candle_data(symbol, interval, max(period + 20, 100))
            
            if df.empty or len(df) < period + 1:
                return json.dumps({"error": "Insufficient data for Bollinger Bands calculation"}, ensure_ascii=False, indent=2)
            
            upper_band, middle_band, lower_band = calculate_bollinger_bands(df['close'], period, std_dev)
            
            current_price = df['close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_middle = middle_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            if pd.isna(current_upper) or pd.isna(current_middle) or pd.isna(current_lower):
                return json.dumps({"error": "Bollinger Bands calculation failed"}, ensure_ascii=False, indent=2)
            
            band_width = ((current_upper - current_lower) / current_middle) * 100
            price_position = ((current_price - current_lower) / (current_upper - current_lower)) * 100
            
            if current_price >= current_upper:
                signal = "Upper band touch - Overbought, consider selling"
                strength = "Strong"
            elif current_price <= current_lower:
                signal = "Lower band touch - Oversold, consider buying"
                strength = "Strong"
            elif current_price > current_middle:
                signal = "Above middle line - Uptrend"
                strength = "Medium"
            else:
                signal = "Below middle line - Downtrend"
                strength = "Medium"
            
            squeeze_threshold = 10
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
                    "volatility": "Low" if band_width < 10 else "Medium" if band_width < 20 else "High"
                },
                "trading_insight": {
                    "squeeze_breakout": "Waiting for volatility breakout" if is_squeeze else "Normal volatility",
                    "mean_reversion": f"Distance to middle line: {abs(float(current_price - current_middle)):.2f}"
                },
                "timestamp": df['datetime'].iloc[-1].isoformat()
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def comprehensive_technical_analysis(symbol: str, interval: str = "1h") -> str:
        """
        Comprehensive technical analysis combining RSI, moving averages, and Bollinger Bands with trading signals.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT, ETHUSDT)
            interval: Time interval for comprehensive analysis
        """
        try:
            df = get_candle_data(symbol, interval, 200)
            
            if df.empty or len(df) < 50:
                return json.dumps({"error": "Insufficient data for comprehensive analysis"}, ensure_ascii=False, indent=2)
            
            results = {}
            total_score = 0
            signals = []
            
            # RSI Analysis
            try:
                rsi = calculate_rsi(df['close'], 14)
                current_rsi = rsi.iloc[-1]
                
                if not pd.isna(current_rsi):
                    if current_rsi <= 30:
                        signals.append("RSI: Oversold - Buy signal")
                        total_score += 1
                        if current_rsi <= 20:
                            total_score += 1
                    elif current_rsi >= 70:
                        signals.append("RSI: Overbought - Sell signal")
                        total_score -= 1
                        if current_rsi >= 80:
                            total_score -= 1
                    else:
                        signals.append("RSI: Neutral")
                    
                    results["rsi"] = {
                        "current": round(float(current_rsi), 2),
                        "signal": "Oversold" if current_rsi <= 30 else "Overbought" if current_rsi >= 70 else "Neutral"
                    }
                else:
                    signals.append("RSI: Calculation failed")
            except Exception as e:
                signals.append(f"RSI: Error ({str(e)})")
            
            # Moving Average Analysis
            try:
                ma_20 = calculate_moving_average(df['close'], 20).iloc[-1]
                ma_50 = calculate_moving_average(df['close'], 50).iloc[-1]
                current_price = df['close'].iloc[-1]
                
                if not pd.isna(ma_20) and not pd.isna(ma_50):
                    if len(df) > 1:
                        prev_ma_20 = calculate_moving_average(df['close'], 20).iloc[-2]
                        prev_ma_50 = calculate_moving_average(df['close'], 50).iloc[-2]
                        
                        if prev_ma_20 <= prev_ma_50 and ma_20 > ma_50:
                            signals.append("Moving Average: Golden Cross - Strong buy")
                            total_score += 2
                        elif prev_ma_20 >= prev_ma_50 and ma_20 < ma_50:
                            signals.append("Moving Average: Death Cross - Strong sell")
                            total_score -= 2
                        else:
                            if current_price > ma_20 > ma_50:
                                signals.append("Moving Average: Bullish alignment")
                                total_score += 1
                            elif current_price < ma_20 < ma_50:
                                signals.append("Moving Average: Bearish alignment")
                                total_score -= 1
                            else:
                                signals.append("Moving Average: Mixed signals")
                    
                    results["moving_average"] = {
                        "ma_20": round(float(ma_20), 2),
                        "ma_50": round(float(ma_50), 2),
                        "current_price": round(float(current_price), 2),
                        "trend": "Bullish" if ma_20 > ma_50 else "Bearish"
                    }
                else:
                    signals.append("Moving Average: Calculation failed")
            except Exception as e:
                signals.append(f"Moving Average: Error ({str(e)})")
            
            # Bollinger Bands Analysis
            try:
                upper_band, middle_band, lower_band = calculate_bollinger_bands(df['close'], 20, 2)
                current_upper = upper_band.iloc[-1]
                current_middle = middle_band.iloc[-1]
                current_lower = lower_band.iloc[-1]
                
                if not pd.isna(current_upper) and not pd.isna(current_lower):
                    if current_price >= current_upper:
                        signals.append("Bollinger Bands: Upper band touch - Consider selling")
                        total_score -= 1
                    elif current_price <= current_lower:
                        signals.append("Bollinger Bands: Lower band touch - Consider buying")
                        total_score += 1
                    else:
                        signals.append("Bollinger Bands: Within normal range")
                    
                    results["bollinger_bands"] = {
                        "upper": round(float(current_upper), 2),
                        "middle": round(float(current_middle), 2),
                        "lower": round(float(current_lower), 2),
                        "position": round(((current_price - current_lower) / (current_upper - current_lower)) * 100, 1)
                    }
                else:
                    signals.append("Bollinger Bands: Calculation failed")
            except Exception as e:
                signals.append(f"Bollinger Bands: Error ({str(e)})")
            
            # Overall Signal Generation
            if total_score >= 3:
                overall_signal = "Strong Buy Recommendation"
                recommendation = "Multiple indicators show buy signals. However, proper risk management is essential."
            elif total_score >= 1:
                overall_signal = "Consider Buying"
                recommendation = "Some indicators show buy signals. Confirm with additional analysis before deciding."
            elif total_score <= -3:
                overall_signal = "Strong Sell Recommendation"
                recommendation = "Multiple indicators show sell signals. Consider stop-loss implementation."
            elif total_score <= -1:
                overall_signal = "Consider Selling"
                recommendation = "Some indicators show sell signals. Monitor closely for trend confirmation."
            else:
                overall_signal = "Neutral - Wait"
                recommendation = "No clear signals detected. Wait for trend confirmation before entering positions."
            
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
                "risk_warning": "This analysis is for reference only. Investment decisions are your own responsibility. Setting stop-loss is recommended."
            }
            
            return json.dumps(comprehensive_result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Comprehensive analysis error: {str(e)}"}, ensure_ascii=False, indent=2)
    
    print("📊 Technical analysis tools registered successfully")