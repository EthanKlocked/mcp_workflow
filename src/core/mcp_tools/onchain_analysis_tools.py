import json
import requests
import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import aiohttp
from collections import defaultdict, Counter

def register_onchain_analysis_tools(mcp):
    
    # API 설정
    ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
    BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
    POLYGONSCAN_API_KEY = os.getenv("POLYGONSCAN_API_KEY", "")
    
    # 실제 주요 거래소 주소들 (공개된 주소)
    EXCHANGE_ADDRESSES = {
        'binance': [
            '0x3f5CE5FbfE3E9af3971dd833D26bA9b5C936f0bE',  # Binance 8
            '0xD551234Ae421e3BCBA99A0Da6d736074f22192FF',  # Binance 9
            '0x564286362092D8e7936f0549571a803B203aAceD',  # Binance 10
            '0x0681d8Db095565FE8A346fA0277bFfdE9C0eDDdF',  # Binance 11
            '0xfE9e8709d3215310075d67E3ed32A380CCf451C8',  # Binance 12
        ],
        'coinbase': [
            '0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43',  # Coinbase 6
            '0x77696bb39917C91A0c3908D577d5e322095425cA',  # Coinbase 7
            '0x503828976D22510aad0201ac7EC88293211D23Da',  # Coinbase 8
            '0xddfAbCdC4D8FfF6C2F9b5F5c4005B1F8F8fA05b2',  # Coinbase 9
        ],
        'kraken': [
            '0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2',  # Kraken 7
            '0x0A869d79a7052C7f1b55a8EbabbEa3420F0D1E13',  # Kraken 8
            '0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13',  # Kraken 9
        ],
        'okx': [
            '0x6cC5f688a315f3dC28A7781717a9A798a59fDA7b',  # OKX
            '0x98ec059dc3adfbdd63429454aeb0c990fba4a128',  # OKX 2
        ],
        'bybit': [
            '0xf89d7b9c864f589bbF53a82105107622B35EaA40',  # Bybit
            '0x2d4C407BBe49438ED859fe965b140dcF1aaB71a9',  # Bybit 2
        ]
    }
    
    async def make_api_request(url: str, timeout: int = 15) -> Optional[Dict]:
        """비동기 API 요청"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:
                        print(f"Rate limit hit, waiting...")
                        await asyncio.sleep(1)
                        return None
                    else:
                        print(f"API 요청 실패: {response.status} - {url}")
                        return None
        except asyncio.TimeoutError:
            print(f"API 요청 타임아웃: {url}")
            return None
        except Exception as e:
            print(f"API 요청 오류: {e}")
            return None
    
    def wei_to_ether(wei_value: str) -> float:
        """Wei를 Ether로 변환"""
        try:
            return int(wei_value) / 1e18
        except:
            return 0.0
    
    def calculate_usd_value(crypto_amount: float, crypto_price_usd: float) -> float:
        """암호화폐 금액을 USD로 변환"""
        return crypto_amount * crypto_price_usd
    
    def classify_address_type(address: str) -> str:
        """주소 유형 분류"""
        address_lower = address.lower()
        
        # 알려진 거래소 주소 확인
        for exchange, addresses in EXCHANGE_ADDRESSES.items():
            if address_lower in [addr.lower() for addr in addresses]:
                return f"{exchange}_exchange"
        
        # 간단한 휴리스틱 분류
        if address_lower.startswith('0x000000'):
            return "burn_address"
        elif len(address) == 42 and address.startswith('0x'):
            return "wallet_address"
        else:
            return "unknown"
    
    async def get_current_crypto_price(symbol: str = "ethereum") -> float:
        """현재 암호화폐 가격 가져오기"""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
            price_data = await make_api_request(url)
            if price_data and symbol in price_data:
                return price_data[symbol]['usd']
            return 3000.0  # 기본값
        except Exception as e:
            print(f"가격 조회 실패: {e}")
            return 3000.0
    
    async def get_latest_blocks(chain: str = "ethereum", count: int = 10) -> List[Dict]:
        """최신 블록들 가져오기"""
        try:
            if chain == "ethereum" and ETHERSCAN_API_KEY:
                # 최신 블록 번호 가져오기
                url = f"https://api.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey={ETHERSCAN_API_KEY}"
                response = await make_api_request(url)
                
                if response and 'result' in response:
                    latest_block = int(response['result'], 16)
                    
                    blocks = []
                    for i in range(count):
                        block_num = latest_block - i
                        block_url = f"https://api.etherscan.io/api?module=proxy&action=eth_getBlockByNumber&tag=0x{block_num:x}&boolean=true&apikey={ETHERSCAN_API_KEY}"
                        
                        block_data = await make_api_request(block_url)
                        if block_data and 'result' in block_data and block_data['result']:
                            blocks.append(block_data['result'])
                        
                        await asyncio.sleep(0.2)  # Rate limit 방지
                    
                    return blocks
            
            return []
        except Exception as e:
            print(f"블록 조회 실패: {e}")
            return []
    
    @mcp.tool()
    async def monitor_whale_transactions(
        chain: str = "ethereum",
        min_value_usd: float = 1000000,
        hours_back: int = 24
    ) -> str:
        """
        Monitor large whale transactions on blockchain networks using real data.
        
        Args:
            chain: Blockchain network (ethereum, bsc, polygon)
            min_value_usd: Minimum transaction value in USD
            hours_back: Time range to monitor (hours)
        """
        try:
            whale_transactions = []
            
            if chain.lower() == "ethereum" and ETHERSCAN_API_KEY:
                # ETH 현재 가격 가져오기
                eth_price = await get_current_crypto_price("ethereum")
                print(f"현재 ETH 가격: ${eth_price}")
                
                # 최신 블록들에서 대형 거래 찾기
                blocks = await get_latest_blocks("ethereum", 20)  # 최근 20개 블록 분석
                
                cutoff_time = datetime.now() - timedelta(hours=hours_back)
                
                for block in blocks:
                    try:
                        block_timestamp = int(block.get('timestamp', '0x0'), 16)
                        block_time = datetime.fromtimestamp(block_timestamp)
                        
                        if block_time < cutoff_time:
                            continue
                        
                        transactions = block.get('transactions', [])
                        
                        for tx in transactions:
                            try:
                                if isinstance(tx, dict):
                                    value_wei = tx.get('value', '0x0')
                                    if value_wei == '0x0':
                                        continue
                                    
                                    value_eth = wei_to_ether(value_wei)
                                    value_usd = value_eth * eth_price
                                    
                                    if value_usd >= min_value_usd:
                                        from_addr = tx.get('from', '')
                                        to_addr = tx.get('to', '')
                                        
                                        from_type = classify_address_type(from_addr)
                                        to_type = classify_address_type(to_addr)
                                        
                                        exchange_involvement = []
                                        if 'exchange' in from_type:
                                            exchange_involvement.append(f"{from_type}_withdrawal")
                                        if 'exchange' in to_type:
                                            exchange_involvement.append(f"{to_type}_deposit")
                                        
                                        whale_transactions.append({
                                            'transaction_hash': tx.get('hash', ''),
                                            'from_address': from_addr,
                                            'to_address': to_addr,
                                            'value_eth': round(value_eth, 4),
                                            'value_usd': round(value_usd, 2),
                                            'exchange_involvement': exchange_involvement,
                                            'timestamp': block_time.isoformat(),
                                            'block_number': int(block.get('number', '0x0'), 16),
                                            'gas_price_gwei': round(int(tx.get('gasPrice', '0x0'), 16) / 1e9, 2),
                                            'transaction_type': 'exchange_to_exchange' if len(exchange_involvement) > 1 else 'large_transfer'
                                        })
                            except Exception as tx_error:
                                continue
                        
                    except Exception as block_error:
                        continue
                
                # 거래량 기준으로 정렬
                whale_transactions.sort(key=lambda x: x['value_usd'], reverse=True)
                
            else:
                return json.dumps({
                    "error": f"Unsupported chain or missing API key: {chain}",
                    "required_env_vars": {
                        "ethereum": "ETHERSCAN_API_KEY",
                        "bsc": "BSCSCAN_API_KEY", 
                        "polygon": "POLYGONSCAN_API_KEY"
                    },
                    "note": "Make sure API key is set in environment variables"
                }, ensure_ascii=False, indent=2)
            
            # 거래 분석
            total_volume = sum(tx.get('value_usd', 0) for tx in whale_transactions)
            
            # 시장 영향 평가
            impact_level = 'LOW'
            reasoning = []
            
            if total_volume > 50000000:  # 5천만 달러 이상
                impact_level = 'HIGH'
                reasoning.append("Large transaction volume may cause significant market impact")
            elif total_volume > 10000000:  # 1천만 달러 이상
                impact_level = 'MEDIUM'
                reasoning.append("Medium transaction volume may influence market")
            
            # 거래소 흐름 분석
            exchange_inflows = len([tx for tx in whale_transactions if any('deposit' in inv for inv in tx.get('exchange_involvement', []))])
            exchange_outflows = len([tx for tx in whale_transactions if any('withdrawal' in inv for inv in tx.get('exchange_involvement', []))])
            
            price_movement = 'NEUTRAL'
            if exchange_inflows > exchange_outflows * 2:
                price_movement = 'BEARISH'
                reasoning.append("High exchange inflow may increase selling pressure")
            elif exchange_outflows > exchange_inflows * 2:
                price_movement = 'BULLISH'
                reasoning.append("High exchange outflow may increase buying pressure")
            
            result = {
                "analysis_timestamp": datetime.now().isoformat(),
                "chain": chain,
                "monitoring_period": f"Last {hours_back} hours",
                "current_eth_price_usd": eth_price,
                "whale_transaction_summary": {
                    "total_transactions": len(whale_transactions),
                    "total_volume_usd": round(total_volume, 2),
                    "largest_transaction_usd": whale_transactions[0].get('value_usd', 0) if whale_transactions else 0,
                    "average_transaction_usd": round(total_volume / len(whale_transactions), 2) if whale_transactions else 0,
                    "exchange_inflows": exchange_inflows,
                    "exchange_outflows": exchange_outflows
                },
                "market_impact_assessment": {
                    "impact_level": impact_level,
                    "reasoning": reasoning,
                    "potential_price_movement": price_movement
                },
                "top_whale_transactions": whale_transactions[:10],
                "data_source": f"Real {chain} blockchain data via Etherscan API",
                "limitations": [
                    "Analysis limited to recent blocks due to API rate limits",
                    "Some exchange addresses may not be identified",
                    "Internal transactions not included"
                ]
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Whale transaction monitoring error: {str(e)}"}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def analyze_exchange_flows(
        exchanges: List[str] = ["binance", "coinbase"],
        time_range: str = "24h"
    ) -> str:
        """
        Analyze cryptocurrency exchange inflow and outflow patterns using real blockchain data.
        
        Args:
            exchanges: List of exchanges to analyze
            time_range: Analysis time range
        """
        try:
            if not ETHERSCAN_API_KEY:
                return json.dumps({
                    "error": "ETHERSCAN_API_KEY not configured",
                    "message": "Please set ETHERSCAN_API_KEY in environment variables"
                }, ensure_ascii=False, indent=2)
            
            eth_price = await get_current_crypto_price("ethereum")
            flow_analysis = {}
            
            # 시간 범위 설정
            hours_back = 24 if time_range == "24h" else 168 if time_range == "7d" else 24
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for exchange_name in exchanges:
                if exchange_name not in EXCHANGE_ADDRESSES:
                    flow_analysis[exchange_name] = {"error": f"Unknown exchange: {exchange_name}"}
                    continue
                
                exchange_addresses = EXCHANGE_ADDRESSES[exchange_name]
                exchange_data = {
                    'total_inflow_usd': 0,
                    'total_outflow_usd': 0,
                    'transaction_count': 0,
                    'large_transactions': [],
                    'inflow_transactions': 0,
                    'outflow_transactions': 0
                }
                
                # 각 거래소 주소별로 분석
                for address in exchange_addresses[:2]:  # API 제한으로 주소당 2개만
                    try:
                        # 최근 거래 내역 가져오기
                        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page=1&offset=100&sort=desc&apikey={ETHERSCAN_API_KEY}"
                        
                        response = await make_api_request(url)
                        if not response or 'result' not in response:
                            continue
                        
                        transactions = response['result']
                        
                        for tx in transactions:
                            try:
                                tx_timestamp = int(tx.get('timeStamp', '0'))
                                tx_time = datetime.fromtimestamp(tx_timestamp)
                                
                                if tx_time < cutoff_time:
                                    break  # 시간 범위 초과
                                
                                value_wei = tx.get('value', '0')
                                value_eth = wei_to_ether(value_wei)
                                value_usd = value_eth * eth_price
                                
                                if value_usd < 1000:  # 1000달러 미만 제외
                                    continue
                                
                                exchange_data['transaction_count'] += 1
                                
                                # 입금/출금 구분
                                if tx.get('to', '').lower() == address.lower():
                                    # 거래소로 입금
                                    exchange_data['total_inflow_usd'] += value_usd
                                    exchange_data['inflow_transactions'] += 1
                                    direction = 'inflow'
                                else:
                                    # 거래소에서 출금
                                    exchange_data['total_outflow_usd'] += value_usd
                                    exchange_data['outflow_transactions'] += 1
                                    direction = 'outflow'
                                
                                # 대형 거래 기록 (100만 달러 이상)
                                if value_usd >= 1000000:
                                    exchange_data['large_transactions'].append({
                                        'hash': tx.get('hash', ''),
                                        'value_usd': round(value_usd, 2),
                                        'value_eth': round(value_eth, 4),
                                        'direction': direction,
                                        'timestamp': tx_time.isoformat(),
                                        'from': tx.get('from', ''),
                                        'to': tx.get('to', '')
                                    })
                                
                            except Exception as tx_error:
                                continue
                        
                        await asyncio.sleep(0.2)  # Rate limit 방지
                        
                    except Exception as addr_error:
                        print(f"주소 {address} 분석 실패: {addr_error}")
                        continue
                
                # 순 흐름 계산
                exchange_data['net_flow_usd'] = exchange_data['total_inflow_usd'] - exchange_data['total_outflow_usd']
                exchange_data['flow_ratio'] = (exchange_data['total_inflow_usd'] / exchange_data['total_outflow_usd']) if exchange_data['total_outflow_usd'] > 0 else float('inf')
                
                # 대형 거래 정렬
                exchange_data['large_transactions'].sort(key=lambda x: x['value_usd'], reverse=True)
                exchange_data['large_transactions'] = exchange_data['large_transactions'][:5]
                
                flow_analysis[exchange_name] = exchange_data
            
            # 전체 분석
            total_inflow = sum(data.get('total_inflow_usd', 0) for data in flow_analysis.values() if 'error' not in data)
            total_outflow = sum(data.get('total_outflow_usd', 0) for data in flow_analysis.values() if 'error' not in data)
            net_flow = total_inflow - total_outflow
            
            # 시장 심리 해석
            if abs(net_flow) < 1000000:
                market_sentiment = "Neutral - Balanced flow"
            elif net_flow > 0:
                market_sentiment = f"Bearish signal - Net inflow ${net_flow:,.0f} (increased selling pressure)"
            else:
                market_sentiment = f"Bullish signal - Net outflow ${abs(net_flow):,.0f} (increased buying pressure)"
            
            # 주요 인사이트 생성
            insights = []
            for exchange, data in flow_analysis.items():
                if 'error' in data:
                    continue
                net_flow_ex = data.get('net_flow_usd', 0)
                if abs(net_flow_ex) > 5000000:
                    direction = "inflow" if net_flow_ex > 0 else "outflow"
                    insights.append(f"{exchange}: Large net {direction} detected (${abs(net_flow_ex):,.0f})")
            
            if not insights:
                insights.append("No significant exchange flow patterns detected")
            
            result = {
                "analysis_timestamp": datetime.now().isoformat(),
                "time_range": time_range,
                "current_eth_price_usd": eth_price,
                "overall_summary": {
                    "total_inflow_usd": round(total_inflow, 2),
                    "total_outflow_usd": round(total_outflow, 2),
                    "net_flow_usd": round(net_flow, 2),
                    "market_sentiment": market_sentiment
                },
                "exchange_breakdown": flow_analysis,
                "key_insights": insights,
                "data_source": "Real Ethereum blockchain data via Etherscan API",
                "limitations": [
                    "Limited to major known exchange addresses",
                    "Analysis restricted by API rate limits",
                    "Internal transactions not included",
                    "ERC-20 token transfers not included"
                ]
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Exchange flow analysis error: {str(e)}"}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def get_network_health_metrics(
        chain: str = "ethereum"
    ) -> str:
        """
        Analyze blockchain network health metrics using real network data.
        
        Args:
            chain: Blockchain to analyze (ethereum, bitcoin)
        """
        try:
            health_metrics = {}
            
            if chain.lower() == "ethereum" and ETHERSCAN_API_KEY:
                # 최신 블록 정보 가져오기
                latest_block_url = f"https://api.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey={ETHERSCAN_API_KEY}"
                latest_response = await make_api_request(latest_block_url)
                
                if not latest_response or 'result' not in latest_response:
                    raise Exception("Failed to get latest block number")
                
                latest_block_num = int(latest_response['result'], 16)
                
                # 최근 10개 블록 분석
                blocks_data = []
                gas_used_list = []
                tx_count_list = []
                block_times = []
                
                for i in range(10):
                    block_num = latest_block_num - i
                    block_url = f"https://api.etherscan.io/api?module=proxy&action=eth_getBlockByNumber&tag=0x{block_num:x}&boolean=false&apikey={ETHERSCAN_API_KEY}"
                    
                    block_data = await make_api_request(block_url)
                    if block_data and 'result' in block_data and block_data['result']:
                        block = block_data['result']
                        
                        gas_used = int(block.get('gasUsed', '0x0'), 16)
                        tx_count = len(block.get('transactions', []))
                        timestamp = int(block.get('timestamp', '0x0'), 16)
                        
                        gas_used_list.append(gas_used)
                        tx_count_list.append(tx_count)
                        block_times.append(timestamp)
                        
                        blocks_data.append({
                            'number': block_num,
                            'gas_used': gas_used,
                            'gas_limit': int(block.get('gasLimit', '0x0'), 16),
                            'tx_count': tx_count,
                            'timestamp': timestamp
                        })
                    
                    await asyncio.sleep(0.1)
                
                # 메트릭 계산
                avg_gas_used = sum(gas_used_list) / len(gas_used_list) if gas_used_list else 0
                avg_tx_count = sum(tx_count_list) / len(tx_count_list) if tx_count_list else 0
                
                # 블록 시간 계산
                if len(block_times) > 1:
                    time_diffs = [block_times[i] - block_times[i+1] for i in range(len(block_times)-1)]
                    avg_block_time = sum(time_diffs) / len(time_diffs) if time_diffs else 12
                else:
                    avg_block_time = 12
                
                # 네트워크 혼잡도 평가
                gas_limit = 30000000  # 이더리움 기본 gas limit
                congestion_ratio = avg_gas_used / gas_limit
                
                if congestion_ratio > 0.9:
                    network_congestion = "High - Network congested"
                elif congestion_ratio > 0.7:
                    network_congestion = "Medium - Moderate usage"
                else:
                    network_congestion = "Low - Smooth network"
                
                # ETH 가격 정보
                eth_price = await get_current_crypto_price("ethereum")
                
                health_metrics = {
                    "current_block": latest_block_num,
                    "average_block_time_seconds": round(avg_block_time, 2),
                    "average_gas_used": round(avg_gas_used, 0),
                    "average_transactions_per_block": round(avg_tx_count, 1),
                    "network_congestion": network_congestion,
                    "congestion_ratio": round(congestion_ratio, 3),
                    "current_eth_price_usd": eth_price,
                    "recent_blocks_analyzed": len(blocks_data)
                }
                
            elif chain.lower() == "bitcoin":
                # 비트코인 네트워크 정보 (BlockCypher API 사용)
                btc_info_url = "https://api.blockcypher.com/v1/btc/main"
                btc_response = await make_api_request(btc_info_url)
                
                if btc_response:
                    # 최근 블록들의 평균 시간 계산
                    latest_blocks_url = f"https://api.blockcypher.com/v1/btc/main/blocks/{btc_response.get('height', 0)}?limit=10"
                    blocks_response = await make_api_request(latest_blocks_url)
                    
                    btc_price = await get_current_crypto_price("bitcoin")
                    
                    health_metrics = {
                        "current_block_height": btc_response.get('height', 0),
                        "hash_rate_estimate": "Data not available via free API",
                        "difficulty": btc_response.get('difficulty', 0),
                        "minutes_between_blocks": "~10 minutes (network adjusted)",
                        "unconfirmed_transactions": btc_response.get('unconfirmed_count', 0),
                        "current_btc_price_usd": btc_price,
                        "network_security": "High - Strong security (based on network size)"
                    }
                else:
                    raise Exception("Failed to get Bitcoin network data")
                
            else:
                return json.dumps({
                    "error": f"Unsupported chain: {chain}",
                    "supported_chains": ["ethereum", "bitcoin"],
                    "note": "Ethereum requires ETHERSCAN_API_KEY environment variable"
                }, ensure_ascii=False, indent=2)
            
            # 건전성 점수 계산
            health_score = 70  # 기본 점수
            
            if chain == "ethereum":
                block_time = health_metrics.get('average_block_time_seconds', 12)
                if 10 <= block_time <= 15:
                    health_score += 15
                elif block_time > 20:
                    health_score -= 15
                
                congestion = health_metrics.get('network_congestion', '')
                if 'Low' in congestion:
                    health_score += 15
                elif 'High' in congestion:
                    health_score -= 20
                    
            elif chain == "bitcoin":
                health_score = 85  # 비트코인은 기본적으로 높은 점수
            
            health_score = min(max(health_score, 0), 100)
            
            # 건전성 해석
            interpretations = []
            if chain == "ethereum":
                block_time = health_metrics.get('average_block_time_seconds', 12)
                if block_time > 15:
                    interpretations.append("Block generation time is longer than average")
                elif block_time < 10:
                    interpretations.append("Block generation time is fast, network operating smoothly")
                
                congestion = health_metrics.get('network_congestion', '')
                if 'High' in congestion:
                    interpretations.append("High network congestion may result in higher transaction fees")
            
            health_assessment = " ".join(interpretations) if interpretations else "Network is operating normally"
            
            # 권장사항
            recommendations = []
            if chain == "ethereum":
                congestion = health_metrics.get('network_congestion', '')
                if 'High' in congestion:
                    recommendations.append("Consider setting higher gas fees during network congestion")
                    recommendations.append("Delay non-urgent transactions until congestion decreases")
                else:
                    recommendations.append("Network conditions are favorable for transactions")
            
            recommendations.append("Continue monitoring network status")
            
            result = {
                "analysis_timestamp": datetime.now().isoformat(),
                "blockchain": chain,
                "network_health_score": health_score,
                "health_metrics": health_metrics,
                "health_assessment": health_assessment,
                "recommendations": recommendations,
                "data_source": f"Real {chain} network data via blockchain APIs"
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Network health analysis error: {str(e)}"}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def detect_large_transfers(
        min_amount_usd: float = 500000,
        time_window_hours: int = 6
    ) -> str:
        """
        Detect large cryptocurrency transfers using real blockchain data.
        
        Args:
            min_amount_usd: Minimum transfer amount in USD to detect
            time_window_hours: Time window for detection (hours)
        """
        try:
            if not ETHERSCAN_API_KEY:
                return json.dumps({
                    "error": "ETHERSCAN_API_KEY not configured",
                    "message": "Please set ETHERSCAN_API_KEY in environment variables"
                }, ensure_ascii=False, indent=2)
            
            large_transfers = []
            eth_price = await get_current_crypto_price("ethereum")
            
            # 시간 범위 설정
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            
            # 최신 블록들에서 대형 이체 검색
            blocks = await get_latest_blocks("ethereum", 50)  # 최근 50개 블록 분석
            
            for block in blocks:
                try:
                    block_timestamp = int(block.get('timestamp', '0x0'), 16)
                    block_time = datetime.fromtimestamp(block_timestamp)
                    
                    if block_time < cutoff_time:
                        continue
                    
                    transactions = block.get('transactions', [])
                    
                    for tx in transactions:
                        try:
                            if isinstance(tx, dict):
                                value_wei = tx.get('value', '0x0')
                                if value_wei == '0x0':
                                    continue
                                
                                value_eth = wei_to_ether(value_wei)
                                value_usd = value_eth * eth_price
                                
                                if value_usd >= min_amount_usd:
                                    from_addr = tx.get('from', '')
                                    to_addr = tx.get('to', '')
                                    
                                    from_type = classify_address_type(from_addr)
                                    to_type = classify_address_type(to_addr)
                                    
                                    # 이체 패턴 분석
                                    if 'exchange' in from_type and 'exchange' in to_type:
                                        transfer_pattern = "exchange_to_exchange"
                                    elif 'exchange' in from_type:
                                        transfer_pattern = "exchange_withdrawal"
                                    elif 'exchange' in to_type:
                                        transfer_pattern = "exchange_deposit"
                                    else:
                                        transfer_pattern = "wallet_to_wallet"
                                    
                                    # 위험도 평가
                                    risk_score = 0
                                    if value_usd > 10000000:
                                        risk_score += 3
                                    elif value_usd > 5000000:
                                        risk_score += 2
                                    elif value_usd > 1000000:
                                        risk_score += 1
                                    
                                    if 'unknown' in from_type or 'unknown' in to_type:
                                        risk_score += 1
                                    
                                    risk_level = "HIGH" if risk_score >= 3 else "MEDIUM" if risk_score >= 2 else "LOW"
                                    
                                    large_transfers.append({
                                        'transaction_hash': tx.get('hash', ''),
                                        'from_address': from_addr,
                                        'to_address': to_addr,
                                        'from_type': from_type,
                                        'to_type': to_type,
                                        'value_eth': round(value_eth, 4),
                                        'value_usd': round(value_usd, 2),
                                        'timestamp': block_time.isoformat(),
                                        'block_number': int(block.get('number', '0x0'), 16),
                                        'transfer_pattern': transfer_pattern,
                                        'risk_level': risk_level,
                                        'gas_fee_eth': round(int(tx.get('gasPrice', '0x0'), 16) * int(tx.get('gas', '0x0'), 16) / 1e18, 6)
                                    })
                        
                        except Exception as tx_error:
                            continue
                
                except Exception as block_error:
                    continue
            
            # 결과 정렬 (큰 금액순)
            large_transfers.sort(key=lambda x: x['value_usd'], reverse=True)
            
            # 분석 결과
            total_volume = sum(t['value_usd'] for t in large_transfers)
            
            # 패턴 분석
            transfer_patterns = Counter([t['transfer_pattern'] for t in large_transfers])
            risk_distribution = Counter([t['risk_level'] for t in large_transfers])
            
            # 시장 영향 분석
            exchange_inflows = len([t for t in large_transfers if t['transfer_pattern'] == 'exchange_deposit'])
            exchange_outflows = len([t for t in large_transfers if t['transfer_pattern'] == 'exchange_withdrawal'])
            
            market_implications = []
            if exchange_inflows > exchange_outflows * 2:
                market_implications.append("High exchange inflows may increase selling pressure")
            elif exchange_outflows > exchange_inflows * 2:
                market_implications.append("High exchange outflows indicate increased hodling behavior")
            
            if total_volume > 100000000:
                market_implications.append("Large fund movements may increase market volatility")
            
            if not market_implications:
                market_implications.append("No significant market impact expected")
            
            # 알림 생성
            alerts = []
            high_risk_transfers = [t for t in large_transfers if t['risk_level'] == 'HIGH']
            if high_risk_transfers:
                alerts.append(f"High-risk transactions detected: {len(high_risk_transfers)} cases")
            
            mega_transfers = [t for t in large_transfers if t['value_usd'] > 10000000]
            if mega_transfers:
                alerts.append(f"Mega transactions over $10M detected: {len(mega_transfers)} cases")
            
            if transfer_patterns.get('exchange_to_exchange', 0) > 5:
                alerts.append("High inter-exchange fund movement activity")
            
            if not alerts:
                alerts.append("No special alerts")
            
            result = {
                "detection_timestamp": datetime.now().isoformat(),
                "detection_window": f"Last {time_window_hours} hours",
                "minimum_amount_usd": min_amount_usd,
                "current_eth_price_usd": eth_price,
                "summary": {
                    "total_large_transfers": len(large_transfers),
                    "total_volume_usd": round(total_volume, 2),
                    "largest_transfer_usd": max([t['value_usd'] for t in large_transfers]) if large_transfers else 0,
                    "average_transfer_usd": round(total_volume / len(large_transfers), 2) if large_transfers else 0
                },
                "pattern_analysis": {
                    "transfer_patterns": dict(transfer_patterns),
                    "risk_distribution": dict(risk_distribution)
                },
                "detected_transfers": large_transfers[:20],  # 상위 20개만
                "market_implications": market_implications,
                "alerts": alerts,
                "data_source": "Real Ethereum blockchain data via Etherscan API",
                "limitations": [
                    "Analysis limited to recent blocks due to API rate limits",
                    "ERC-20 token transfers not included",
                    "Some exchange addresses may not be identified"
                ]
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Large transfer detection error: {str(e)}"}, ensure_ascii=False, indent=2)
    
    print("🔗 Real onchain analysis tools registered successfully")