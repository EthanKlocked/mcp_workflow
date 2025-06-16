import json
import requests
import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import Counter
import asyncpraw
from textblob import TextBlob
import feedparser

def register_social_sentiment_tools(mcp):
    CRYPTO_PATTERNS = {
        'BTC': r'(?i)\b(bitcoin|btc|₿)\b',
        'ETH': r'(?i)\b(ethereum|eth|ether)\b',
        'BNB': r'(?i)\b(binance|bnb)\b',
        'XRP': r'(?i)\b(ripple|xrp)\b',
        'ADA': r'(?i)\b(cardano|ada)\b',
        'SOL': r'(?i)\b(solana|sol)\b',
        'DOT': r'(?i)\b(polkadot|dot)\b',
        'AVAX': r'(?i)\b(avalanche|avax)\b',
        'LINK': r'(?i)\b(chainlink|link)\b',
        'MATIC': r'(?i)\b(polygon|matic)\b',
        'DOGE': r'(?i)\b(dogecoin|doge)\b',
        'SHIB': r'(?i)\b(shiba|shib)\b'
    }
    
    POSITIVE_WORDS = [
        'moon', 'bullish', 'pump', 'surge', 'rally', 'breakout', 'hodl',
        'diamond hands', 'to the moon', 'bullrun', 'gains', 'profit',
        'bull', 'up', 'high', 'strong', 'buy', 'long', 'invest'
    ]
    
    NEGATIVE_WORDS = [
        'dump', 'crash', 'bearish', 'dip', 'fall', 'panic', 'fud',
        'paper hands', 'rekt', 'loss', 'scam', 'rug pull',
        'bear', 'down', 'low', 'weak', 'sell', 'short'
    ]
    
    def get_reddit_client():
        """Async Reddit 클라이언트 초기화"""
        try:
            return asyncpraw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent="python:crypto_sentiment:v1.0 (by /u/SoilPsychological806)"  # ✅ 수정됨
            )
        except Exception as e:
            print(f"Reddit 클라이언트 초기화 실패: {e}")
            return None
    
    def extract_crypto_mentions(text: str) -> List[str]:
        """텍스트에서 암호화폐 언급 추출"""
        import re
        mentions = []
        text_lower = text.lower()
        
        for symbol, pattern in CRYPTO_PATTERNS.items():
            if re.search(pattern, text):
                mentions.append(symbol)
        
        return mentions
    
    def analyze_text_sentiment(text: str) -> Dict:
        """텍스트 감정 분석"""
        text_lower = text.lower()
        
        # TextBlob 감정 분석
        blob_sentiment = TextBlob(text).sentiment
        
        # 키워드 기반 감정 분석
        positive_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
        negative_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)
        
        # 종합 점수 계산
        keyword_score = positive_count - negative_count
        combined_score = (blob_sentiment.polarity + (keyword_score * 0.1)) / 2
        
        # 감정 분류
        if combined_score > 0.1:
            sentiment = "positive"
        elif combined_score < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return {
            'sentiment': sentiment,
            'score': round(combined_score, 3),
            'confidence': round(abs(combined_score), 3),
            'positive_signals': positive_count,
            'negative_signals': negative_count,
            'textblob_polarity': round(blob_sentiment.polarity, 3),
            'textblob_subjectivity': round(blob_sentiment.subjectivity, 3)
        }
    
    @mcp.tool()
    async def analyze_reddit_crypto_sentiment(
        subreddits: List[str] = ["CryptoCurrency", "Bitcoin", "ethereum"],
        post_limit: int = 50,
        time_filter: str = "day"
    ) -> str:
        """
        Analyze cryptocurrency community sentiment from Reddit with async support.
        
        Args:
            subreddits: List of subreddits to analyze
            post_limit: Number of posts to analyze per subreddit
            time_filter: Time filter (hour, day, week, month, year, all)
        """
        try:
            reddit = get_reddit_client()
            if not reddit:
                return json.dumps({"error": "Reddit API connection failed. Please check environment variables."}, ensure_ascii=False, indent=2)
            
            analysis_results = {}
            overall_stats = {
                'total_posts': 0,
                'total_comments': 0,
                'crypto_mentions': Counter(),
                'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
                'average_sentiment': 0,
                'high_engagement_topics': []
            }
            
            for subreddit_name in subreddits:
                try:
                    subreddit = await reddit.subreddit(subreddit_name, fetch=True)                     
                    posts = []
                    
                    if time_filter == "hour":
                        async for post in subreddit.top(time_filter="hour", limit=post_limit):
                            posts.append(post)
                    elif time_filter == "day":
                        async for post in subreddit.hot(limit=post_limit):
                            posts.append(post)
                    else:
                        async for post in subreddit.top(time_filter=time_filter, limit=post_limit):
                            posts.append(post)
                    
                    subreddit_data = {
                        'posts_analyzed': len(posts),
                        'sentiment_scores': [],
                        'crypto_mentions': Counter(),
                        'top_posts': [],
                        'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0}
                    }
                    
                    for post in posts:
                        try:
                            full_text = f"{post.title} {getattr(post, 'selftext', '')}"
                            
                            # 감정 분석
                            sentiment_analysis = analyze_text_sentiment(full_text)
                            
                            # 암호화폐 언급 추출
                            crypto_mentions = extract_crypto_mentions(full_text)
                            
                            # 데이터 집계
                            subreddit_data['sentiment_scores'].append(sentiment_analysis['score'])
                            subreddit_data['sentiment_distribution'][sentiment_analysis['sentiment']] += 1
                            
                            for crypto in crypto_mentions:
                                subreddit_data['crypto_mentions'][crypto] += 1
                                overall_stats['crypto_mentions'][crypto] += 1
                            
                            # 높은 참여도 게시물 저장
                            engagement_score = post.score + post.num_comments
                            if engagement_score > 50:  # 임계값
                                subreddit_data['top_posts'].append({
                                    'title': post.title[:100] + '...' if len(post.title) > 100 else post.title,
                                    'score': post.score,
                                    'comments': post.num_comments,
                                    'sentiment': sentiment_analysis['sentiment'],
                                    'crypto_mentions': crypto_mentions,
                                    'url': f"https://reddit.com{post.permalink}"
                                })
                        except Exception as e:
                            # 개별 게시물 처리 오류는 건너뜀
                            continue
                    
                    # 서브레딧별 통계 계산
                    if subreddit_data['sentiment_scores']:
                        avg_sentiment = sum(subreddit_data['sentiment_scores']) / len(subreddit_data['sentiment_scores'])
                        subreddit_data['average_sentiment'] = round(avg_sentiment, 3)
                        
                        # 상위 게시물 정렬
                        subreddit_data['top_posts'].sort(
                            key=lambda x: x['score'] + x['comments'], 
                            reverse=True
                        )
                        subreddit_data['top_posts'] = subreddit_data['top_posts'][:5]
                        
                        # 가장 언급된 암호화폐
                        subreddit_data['top_mentioned_cryptos'] = dict(subreddit_data['crypto_mentions'].most_common(5))
                    
                    analysis_results[subreddit_name] = subreddit_data
                    
                    # 전체 통계 업데이트
                    overall_stats['total_posts'] += subreddit_data['posts_analyzed']
                    for sentiment, count in subreddit_data['sentiment_distribution'].items():
                        overall_stats['sentiment_distribution'][sentiment] += count
                    
                    # API rate limit 방지
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    analysis_results[subreddit_name] = {"error": f"Subreddit analysis failed: {str(e)}"}
            
            # Reddit 연결 종료
            await reddit.close()
            
            # 전체 평균 감정 계산
            total_posts = overall_stats['total_posts']
            if total_posts > 0:
                all_scores = []
                for subreddit_data in analysis_results.values():
                    if 'sentiment_scores' in subreddit_data:
                        all_scores.extend(subreddit_data['sentiment_scores'])
                
                if all_scores:
                    overall_stats['average_sentiment'] = round(sum(all_scores) / len(all_scores), 3)
            
            # 상위 언급 암호화폐
            overall_stats['top_mentioned_cryptos'] = dict(overall_stats['crypto_mentions'].most_common(10))
            
            # 시장 심리 요약
            total_sentiment_posts = sum(overall_stats['sentiment_distribution'].values())
            if total_sentiment_posts > 0:
                sentiment_percentages = {
                    sentiment: round((count / total_sentiment_posts) * 100, 1)
                    for sentiment, count in overall_stats['sentiment_distribution'].items()
                }
                
                # 시장 심리 판단
                if sentiment_percentages['positive'] > 50:
                    market_mood = "Strong optimism"
                elif sentiment_percentages['positive'] > 35:
                    market_mood = "Mild optimism"
                elif sentiment_percentages['negative'] > 50:
                    market_mood = "Strong pessimism"
                elif sentiment_percentages['negative'] > 35:
                    market_mood = "Mild pessimism"
                else:
                    market_mood = "Neutral"
            else:
                sentiment_percentages = {}
                market_mood = "Insufficient data"
            
            # 최종 결과
            final_result = {
                "analysis_timestamp": datetime.now().isoformat(),
                "analysis_period": f"Recent {time_filter}",
                "market_sentiment_summary": {
                    "overall_mood": market_mood,
                    "average_sentiment_score": overall_stats['average_sentiment'],
                    "sentiment_distribution": overall_stats['sentiment_distribution'],
                    "sentiment_percentages": sentiment_percentages,
                    "total_posts_analyzed": overall_stats['total_posts']
                },
                "crypto_mention_analysis": {
                    "total_mentions": sum(overall_stats['crypto_mentions'].values()),
                    "top_mentioned_cryptos": overall_stats['top_mentioned_cryptos'],
                    "trending_cryptos": list(overall_stats['crypto_mentions'].most_common(5))
                },
                "subreddit_breakdown": analysis_results,
                "investment_insight": generate_investment_insight(overall_stats, sentiment_percentages),
                "data_sources": [f"r/{sub}" for sub in subreddits]
            }
            
            return json.dumps(final_result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Analysis error: {str(e)}"}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def monitor_crypto_social_trends(
        keywords: List[str] = ["bitcoin", "ethereum", "altcoin", "defi", "nft"],
        sources: List[str] = ["reddit", "rss"]
    ) -> str:
        """
        Monitor cryptocurrency social trends across multiple platforms with async support.
        
        Args:
            keywords: List of keywords to monitor for trending topics
            sources: Data sources (reddit, rss)
        """
        try:
            trend_data = {}
            
            # Reddit 트렌드 분석
            if "reddit" in sources:
                reddit = get_reddit_client()
                if reddit:
                    reddit_trends = {}
                    subreddits = ["CryptoCurrency", "Bitcoin", "ethereum", "altcoin", "CryptoMarkets"]
                    
                    for subreddit_name in subreddits:
                        try:
                            subreddit = await reddit.subreddit(subreddit_name)                            
                            posts = []
                            async for post in subreddit.hot(limit=25):
                                posts.append(post)
                            
                            keyword_mentions = {keyword: 0 for keyword in keywords}
                            trending_posts = []
                            
                            for post in posts:
                                text = f"{post.title} {getattr(post, 'selftext', '')}".lower()
                                
                                # 키워드 카운트
                                for keyword in keywords:
                                    if keyword.lower() in text:
                                        keyword_mentions[keyword] += 1
                                
                                # 트렌딩 게시물 (높은 참여도)
                                if post.score > 100 or post.num_comments > 50:
                                    sentiment = analyze_text_sentiment(post.title)
                                    trending_posts.append({
                                        'title': post.title,
                                        'score': post.score,
                                        'comments': post.num_comments,
                                        'sentiment': sentiment['sentiment'],
                                        'created_utc': datetime.fromtimestamp(post.created_utc).isoformat()
                                    })
                            
                            reddit_trends[subreddit_name] = {
                                'keyword_mentions': keyword_mentions,
                                'trending_posts': sorted(trending_posts, key=lambda x: x['score'], reverse=True)[:3]
                            }
                            
                            # API rate limit 방지
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            reddit_trends[subreddit_name] = {"error": str(e)}
                    
                    # Reddit 연결 종료
                    await reddit.close()
                    trend_data['reddit'] = reddit_trends
            
            # RSS 피드 트렌드 분석
            if "rss" in sources:
                rss_feeds = {
                    'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
                    'cointelegraph': 'https://cointelegraph.com/rss',
                    'decrypt': 'https://decrypt.co/feed'
                }
                
                rss_trends = {}
                for source_name, feed_url in rss_feeds.items():
                    try:
                        feed = feedparser.parse(feed_url)
                        
                        keyword_mentions = {keyword: 0 for keyword in keywords}
                        recent_articles = []
                        
                        for entry in feed.entries[:20]:  # 최근 20개 기사
                            text = f"{entry.title} {entry.get('summary', '')}".lower()
                            
                            # 키워드 카운트
                            mentioned_keywords = []
                            for keyword in keywords:
                                if keyword.lower() in text:
                                    keyword_mentions[keyword] += 1
                                    mentioned_keywords.append(keyword)
                            
                            if mentioned_keywords:
                                sentiment = analyze_text_sentiment(entry.title)
                                recent_articles.append({
                                    'title': entry.title,
                                    'url': entry.get('link', ''),
                                    'mentioned_keywords': mentioned_keywords,
                                    'sentiment': sentiment['sentiment'],
                                    'published': entry.get('published', '')
                                })
                        
                        rss_trends[source_name] = {
                            'keyword_mentions': keyword_mentions,
                            'recent_articles': recent_articles[:5]
                        }
                        
                    except Exception as e:
                        rss_trends[source_name] = {"error": str(e)}
                
                trend_data['rss'] = rss_trends
            
            # 트렌드 분석 결과
            overall_keyword_trends = Counter()
            for source_data in trend_data.values():
                if isinstance(source_data, dict):
                    for platform_data in source_data.values():
                        if isinstance(platform_data, dict) and 'keyword_mentions' in platform_data:
                            for keyword, count in platform_data['keyword_mentions'].items():
                                overall_keyword_trends[keyword] += count
            
            # 결과 정리
            result = {
                "monitoring_timestamp": datetime.now().isoformat(),
                "trend_summary": {
                    "hottest_keywords": dict(overall_keyword_trends.most_common(5)),
                    "total_mentions": sum(overall_keyword_trends.values()),
                    "trending_analysis": analyze_trending_keywords(overall_keyword_trends)
                },
                "source_breakdown": trend_data,
                "social_momentum_score": calculate_social_momentum(overall_keyword_trends),
                "recommendations": generate_trend_recommendations(overall_keyword_trends)
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Trend monitoring error: {str(e)}"}, ensure_ascii=False, indent=2)
    
    @mcp.tool()
    async def detect_social_anomalies(
        monitoring_period: int = 24,  # 시간
        anomaly_threshold: float = 2.0  # 표준편차 배수
    ) -> str:
        """
        Detect abnormal activity patterns in social media (pump & dump, sudden sentiment shifts, etc.).
        
        Args:
            monitoring_period: Monitoring period in hours
            anomaly_threshold: Anomaly detection threshold (standard deviation multiplier)
        """
        try:
            reddit = get_reddit_client()
            if not reddit:
                return json.dumps({"error": "Reddit API connection failed"}, ensure_ascii=False, indent=2)
            
            anomalies = []
            subreddits_to_monitor = ["CryptoCurrency", "SatoshiStreetBets", "altcoin"]
            
            for subreddit_name in subreddits_to_monitor:
                try:
                    subreddit = await reddit.subreddit(subreddit_name)
                    
                    posts = []
                    async for post in subreddit.new(limit=100):
                        posts.append(post)
                    
                    # 시간별 활동 분석
                    hourly_activity = {}
                    sentiment_by_hour = {}
                    crypto_mentions_by_hour = {}
                    
                    current_time = datetime.now()
                    
                    for post in posts:
                        post_time = datetime.fromtimestamp(post.created_utc)
                        hours_ago = int((current_time - post_time).total_seconds() / 3600)
                        
                        if hours_ago <= monitoring_period:
                            # 시간별 활동량
                            if hours_ago not in hourly_activity:
                                hourly_activity[hours_ago] = 0
                                sentiment_by_hour[hours_ago] = []
                                crypto_mentions_by_hour[hours_ago] = Counter()
                            
                            hourly_activity[hours_ago] += 1
                            
                            # 감정 분석
                            sentiment = analyze_text_sentiment(post.title)
                            sentiment_by_hour[hours_ago].append(sentiment['score'])
                            
                            # 암호화폐 언급
                            crypto_mentions = extract_crypto_mentions(post.title)
                            for crypto in crypto_mentions:
                                crypto_mentions_by_hour[hours_ago][crypto] += 1
                    
                    # 이상 징후 감지
                    if len(hourly_activity) > 5:  # 충분한 데이터가 있을 때만
                        activity_values = list(hourly_activity.values())
                        avg_activity = sum(activity_values) / len(activity_values)
                        
                        if avg_activity > 0:
                            import statistics
                            try:
                                std_activity = statistics.stdev(activity_values)
                                
                                # 활동량 급증 감지
                                for hour, activity in hourly_activity.items():
                                    if activity > avg_activity + (anomaly_threshold * std_activity):
                                        anomalies.append({
                                            'type': 'Activity surge',
                                            'subreddit': subreddit_name,
                                            'hours_ago': hour,
                                            'activity_level': activity,
                                            'average_level': round(avg_activity, 1),
                                            'severity': 'HIGH' if activity > avg_activity + (3 * std_activity) else 'MEDIUM'
                                        })
                                
                                # 감정 급변 감지
                                for hour, sentiments in sentiment_by_hour.items():
                                    if len(sentiments) > 3:
                                        avg_sentiment = sum(sentiments) / len(sentiments)
                                        if abs(avg_sentiment) > 0.5:  # 강한 감정
                                            anomalies.append({
                                                'type': 'Sentiment spike' if avg_sentiment > 0 else 'Fear spreading',
                                                'subreddit': subreddit_name,
                                                'hours_ago': hour,
                                                'sentiment_score': round(avg_sentiment, 3),
                                                'post_count': len(sentiments),
                                                'severity': 'HIGH' if abs(avg_sentiment) > 0.7 else 'MEDIUM'
                                            })
                                
                                # 특정 코인 급증 언급 감지
                                for hour, crypto_counts in crypto_mentions_by_hour.items():
                                    for crypto, count in crypto_counts.items():
                                        if count > 5:  # 시간당 5회 이상 언급
                                            anomalies.append({
                                                'type': 'Coin mention surge',
                                                'subreddit': subreddit_name,
                                                'crypto': crypto,
                                                'hours_ago': hour,
                                                'mention_count': count,
                                                'severity': 'HIGH' if count > 10 else 'MEDIUM'
                                            })
                            
                            except statistics.StatisticsError:
                                # 표준편차 계산 불가 (모든 값이 같을 때)
                                pass
                    
                    # API rate limit 방지
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    anomalies.append({
                        'type': 'Data collection error',
                        'subreddit': subreddit_name,
                        'error': str(e)
                    })
            
            # Reddit 연결 종료
            await reddit.close()
            
            # 심각도별 정렬
            anomalies.sort(key=lambda x: (x.get('severity', 'LOW') == 'HIGH', x.get('hours_ago', 999)))
            
            # 결과 요약
            high_severity = len([a for a in anomalies if a.get('severity') == 'HIGH'])
            medium_severity = len([a for a in anomalies if a.get('severity') == 'MEDIUM'])
            
            result = {
                "detection_timestamp": datetime.now().isoformat(),
                "monitoring_period_hours": monitoring_period,
                "anomaly_summary": {
                    "total_anomalies": len(anomalies),
                    "high_severity": high_severity,
                    "medium_severity": medium_severity,
                    "risk_level": "HIGH" if high_severity > 2 else "MEDIUM" if medium_severity > 3 else "LOW"
                },
                "detected_anomalies": anomalies[:20],  # 상위 20개만
                "analysis_notes": [
                    "Activity surges may indicate pump & dump or major news.",
                    "Sentiment spikes may indicate market psychology changes.",
                    "Coin mention surges may indicate promotional manipulation.",
                    "Always verify with additional analysis and careful judgment."
                ]
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Anomaly detection error: {str(e)}"}, ensure_ascii=False, indent=2)
    
    # 헬퍼 함수들
    def generate_investment_insight(stats: Dict, sentiment_percentages: Dict) -> str:
        """투자 인사이트 생성"""
        insights = []
        
        if sentiment_percentages.get('positive', 0) > 60:
            insights.append("Community sentiment is very optimistic. Watch for potential overheating.")
        elif sentiment_percentages.get('negative', 0) > 60:
            insights.append("Community sentiment is very pessimistic. May present buying opportunities.")
        else:
            insights.append("Community sentiment is stable.")
        
        # 가장 많이 언급된 코인 분석
        if stats['crypto_mentions']:
            top_crypto = stats['crypto_mentions'].most_common(1)[0]
            insights.append(f"{top_crypto[0]} is most mentioned ({top_crypto[1]} times).")
        
        return " ".join(insights)
    
    def analyze_trending_keywords(keyword_trends: Counter) -> str:
        """트렌딩 키워드 분석"""
        if not keyword_trends:
            return "No trending keywords detected."
        
        top_keyword = keyword_trends.most_common(1)[0]
        total_mentions = sum(keyword_trends.values())
        
        if top_keyword[1] > total_mentions * 0.4:
            return f"{top_keyword[0]} is overwhelmingly trending."
        else:
            return "Multiple keywords are receiving balanced attention."
    
    def calculate_social_momentum(keyword_trends: Counter) -> float:
        """소셜 모멘텀 점수 계산 (0-100)"""
        if not keyword_trends:
            return 0.0
        
        total_mentions = sum(keyword_trends.values())
        unique_keywords = len(keyword_trends)
        
        # 기본 점수 (언급 수 기반)
        base_score = min(total_mentions * 2, 80)
        
        # 다양성 보너스
        diversity_bonus = min(unique_keywords * 3, 20)
        
        return min(base_score + diversity_bonus, 100.0)
    
    def generate_trend_recommendations(keyword_trends: Counter) -> List[str]:
        """트렌드 기반 추천사항"""
        recommendations = []
        
        if not keyword_trends:
            return ["Insufficient trend data available."]
        
        top_keywords = keyword_trends.most_common(3)
        
        for keyword, count in top_keywords:
            if count > 10:
                recommendations.append(f"Monitor {keyword} related news and charts.")
        
        if len(recommendations) == 0:
            recommendations.append("No significant trends detected currently.")
        
        recommendations.append("Social trends are for reference only. Combine with technical analysis.")
        
        return recommendations
    
    print("📱 Async social sentiment analysis tools registered successfully")