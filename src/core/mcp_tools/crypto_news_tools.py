import json
import requests
import feedparser
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import re
from urllib.parse import urlparse

def register_crypto_news_tools(mcp):
    
    RSS_FEEDS = {
        'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'cointelegraph': 'https://cointelegraph.com/rss',
        'bitcoinist': 'https://bitcoinist.com/feed/',
        'decrypt': 'https://decrypt.co/feed',
        'cryptoslate': 'https://cryptoslate.com/feed/',
        'cryptopotato': 'https://cryptopotato.com/feed/',
        'cryptonews': 'https://cryptonews.com/news/feed/',
        'newsbtc': 'https://www.newsbtc.com/feed/',
        'cryptocompare': 'https://www.cryptocompare.com/api/data/news/',
        'coingecko_trending': 'https://api.coingecko.com/api/v3/search/trending'
    }
    
    def fetch_rss_feed(url: str, source_name: str) -> List[Dict]:
        try:
            feed = feedparser.parse(url)
            news_list = []
            
            for entry in feed.entries[:10]:
                try:
                    published = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now()
                except:
                    published = datetime.now()
                
                news_list.append({
                    'title': entry.title if hasattr(entry, 'title') else 'No Title',
                    'description': entry.summary if hasattr(entry, 'summary') else entry.description if hasattr(entry, 'description') else '',
                    'url': entry.link if hasattr(entry, 'link') else '',
                    'published_at': published.isoformat(),
                    'source': source_name,
                    'raw_date': str(entry.published) if hasattr(entry, 'published') else ''
                })
            
            return news_list
            
        except Exception as e:
            print(f"RSS feed error ({source_name}): {str(e)}")
            return []
    
    def fetch_cryptocompare_news(limit: int = 10) -> List[Dict]:
        try:
            url = f"https://min-api.cryptocompare.com/data/v2/news/?lang=EN&limit={limit}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                news_list = []
                
                for item in data.get('Data', []):
                    news_list.append({
                        'title': item.get('title', ''),
                        'description': item.get('body', '')[:300] + '...' if len(item.get('body', '')) > 300 else item.get('body', ''),
                        'url': item.get('url', ''),
                        'published_at': datetime.fromtimestamp(item.get('published_on', 0)).isoformat(),
                        'source': 'CryptoCompare',
                        'image_url': item.get('imageurl', ''),
                        'categories': item.get('categories', ''),
                        'lang': item.get('lang', 'EN')
                    })
                
                return news_list
            else:
                print(f"CryptoCompare API error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"CryptoCompare news fetch failed: {e}")
            return []
    
    def fetch_coingecko_trending() -> Dict:
        try:
            url = "https://api.coingecko.com/api/v3/search/trending"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                trending_coins = []
                
                for coin in data.get('coins', []):
                    coin_data = coin.get('item', {})
                    trending_coins.append({
                        'name': coin_data.get('name', ''),
                        'symbol': coin_data.get('symbol', ''),
                        'market_cap_rank': coin_data.get('market_cap_rank', 0),
                        'price_btc': coin_data.get('price_btc', 0),
                        'score': coin_data.get('score', 0)
                    })
                
                return {
                    'trending_coins': trending_coins,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {}
                
        except Exception as e:
            print(f"Trending info fetch failed: {e}")
            return {}
    
    def analyze_sentiment_simple(text: str) -> Dict:
        positive_words = [
            'surge', 'rally', 'bullish', 'gain', 'rise', 'pump', 'moon', 'breakout',
            'adoption', 'partnership', 'upgrade', 'positive', 'growth', 'expansion',
            'bull', 'up', 'high', 'strong', 'buy', 'long', 'invest'
        ]
        
        negative_words = [
            'drop', 'fall', 'bearish', 'crash', 'dump', 'decline', 'concern', 'risk',
            'regulation', 'ban', 'hack', 'scam', 'negative', 'warning', 'threat',
            'bear', 'down', 'low', 'weak', 'sell', 'short'
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            score = min(positive_count - negative_count, 3)
        elif negative_count > positive_count:
            sentiment = "negative"
            score = -min(negative_count - positive_count, 3)
        else:
            sentiment = "neutral"
            score = 0
        
        return {
            'sentiment': sentiment,
            'score': score,
            'positive_signals': positive_count,
            'negative_signals': negative_count
        }
    
    def extract_coins_from_text(text: str) -> List[str]:
        coin_patterns = {
            'BTC': r'(?i)\b(bitcoin|btc)\b',
            'ETH': r'(?i)\b(ethereum|eth|ether)\b',  
            'BNB': r'(?i)\b(binance|bnb)\b',
            'XRP': r'(?i)\b(ripple|xrp)\b',
            'ADA': r'(?i)\b(cardano|ada)\b',
            'SOL': r'(?i)\b(solana|sol)\b',
            'DOT': r'(?i)\b(polkadot|dot)\b',
            'AVAX': r'(?i)\b(avalanche|avax)\b',
            'LINK': r'(?i)\b(chainlink|link)\b',
            'MATIC': r'(?i)\b(polygon|matic)\b'
        }
        
        found_coins = []
        for symbol, pattern in coin_patterns.items():
            if re.search(pattern, text):
                found_coins.append(symbol)
        
        return found_coins
    
    @mcp.tool()
    async def get_latest_crypto_news(sources: List[str] = ["cryptocompare", "coindesk"], limit_per_source: int = 5) -> str:
        """
        Collect latest cryptocurrency news from free sources with sentiment analysis.
        
        Args:
            sources: List of news sources (cryptocompare, coindesk, cointelegraph, etc.)
            limit_per_source: Number of news articles to collect per source
        """
        try:
            all_news = []
            source_status = {}
            
            for source in sources:
                if source == "cryptocompare":
                    news = fetch_cryptocompare_news(limit_per_source)
                    source_status[source] = len(news)
                    all_news.extend(news)
                    
                elif source in RSS_FEEDS:
                    news = fetch_rss_feed(RSS_FEEDS[source], source)
                    source_status[source] = len(news)  
                    all_news.extend(news)
                else:
                    source_status[source] = 0
            
            analyzed_news = []
            sentiment_summary = {'positive': 0, 'negative': 0, 'neutral': 0}
            coin_mentions = {}
            
            for news in all_news:
                sentiment = analyze_sentiment_simple(news['title'] + ' ' + news['description'])
                coins = extract_coins_from_text(news['title'] + ' ' + news['description'])
                
                if sentiment['sentiment'] == 'positive':
                    sentiment_summary['positive'] += 1
                elif sentiment['sentiment'] == 'negative':
                    sentiment_summary['negative'] += 1
                else:
                    sentiment_summary['neutral'] += 1
                
                for coin in coins:
                    coin_mentions[coin] = coin_mentions.get(coin, 0) + 1
                
                analyzed_news.append({
                    **news,
                    'sentiment': sentiment,
                    'mentioned_coins': coins
                })
            
            analyzed_news.sort(key=lambda x: x['published_at'], reverse=True)
            
            result = {
                'summary': {
                    'total_news': len(analyzed_news),
                    'source_status': source_status,
                    'sentiment_distribution': sentiment_summary,
                    'top_mentioned_coins': sorted(coin_mentions.items(), key=lambda x: x[1], reverse=True)[:5],
                    'collection_time': datetime.now().isoformat()
                },
                'news': analyzed_news[:20],
                'available_sources': list(RSS_FEEDS.keys())
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({'error': str(e)}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def get_trending_crypto_info() -> str:
        """
        Get trending cryptocurrency information from CoinGecko free API with related news analysis.
        """
        try:
            trending_data = fetch_coingecko_trending()
            
            if not trending_data:
                return json.dumps({'error': 'Unable to fetch trending information'}, ensure_ascii=False, indent=2)
            
            trending_coins = [coin['symbol'].upper() for coin in trending_data['trending_coins'][:5]]
            
            coin_news = {}
            all_news = fetch_cryptocompare_news(20)
            
            for coin_symbol in trending_coins:
                relevant_news = []
                for news in all_news:
                    if coin_symbol.lower() in (news['title'] + news['description']).lower():
                        sentiment = analyze_sentiment_simple(news['title'] + news['description'])
                        relevant_news.append({
                            'title': news['title'],
                            'url': news['url'],
                            'sentiment': sentiment['sentiment'],
                            'published_at': news['published_at']
                        })
                
                coin_news[coin_symbol] = relevant_news[:3]
            
            result = {
                'trending_analysis': trending_data,
                'trending_coins_news': coin_news,
                'market_insight': {
                    'hot_topics': trending_coins,
                    'analysis_time': datetime.now().isoformat()
                }
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({'error': str(e)}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def monitor_breaking_news(keywords: List[str] = ["bitcoin", "ethereum", "regulation"]) -> str:
        """
        Monitor breaking cryptocurrency news based on specified keywords within recent hours.
        
        Args:
            keywords: List of keywords to monitor for breaking news
        """
        try:
            recent_threshold = datetime.now() - timedelta(hours=3)
            
            all_news = fetch_cryptocompare_news(30)
            breaking_news = []
            
            for news in all_news:
                news_time = datetime.fromisoformat(news['published_at'].replace('Z', '+00:00')).replace(tzinfo=None)
                
                if news_time > recent_threshold:
                    text = (news['title'] + ' ' + news['description']).lower()
                    matched_keywords = [kw for kw in keywords if kw.lower() in text]
                    
                    if matched_keywords:
                        sentiment = analyze_sentiment_simple(news['title'] + news['description'])
                        coins = extract_coins_from_text(text)
                        
                        breaking_news.append({
                            'title': news['title'],
                            'description': news['description'][:200] + '...',
                            'url': news['url'],
                            'published_at': news['published_at'],
                            'matched_keywords': matched_keywords,
                            'sentiment': sentiment,
                            'affected_coins': coins,
                            'urgency': 'HIGH' if len(matched_keywords) > 1 else 'MEDIUM'
                        })
            
            breaking_news.sort(key=lambda x: (x['urgency'] == 'HIGH', x['published_at']), reverse=True)
            
            result = {
                'breaking_news_count': len(breaking_news),
                'monitoring_keywords': keywords,
                'time_range': 'Recent 3 hours',
                'breaking_news': breaking_news[:10],
                'alert_summary': {
                    'high_priority': len([n for n in breaking_news if n['urgency'] == 'HIGH']),
                    'medium_priority': len([n for n in breaking_news if n['urgency'] == 'MEDIUM'])
                }
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({'error': str(e)}, ensure_ascii=False, indent=2)
    
    print("🆓 Free cryptocurrency news tools registered successfully")