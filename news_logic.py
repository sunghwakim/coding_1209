import feedparser
import google.generativeai as genai
from bs4 import BeautifulSoup
from datetime import datetime
import streamlit as st
import requests
import time

def fetch_rss_feeds(feeds_list):
    """RSS 피드 목록에서 뉴스 수집"""
    articles = []
    if not feeds_list: return articles
    
    for feed in feeds_list:
        try:
            feed_url = feed.get('url', '')
            if not feed_url: continue
            parsed = feedparser.parse(feed_url)
            source_name = feed.get('name', 'Unknown Source')
            
            if not parsed.entries: continue
            for entry in parsed.entries[:5]:
                if not hasattr(entry, 'title') or not entry.title: continue
                title = entry.title
                link = entry.get('link', '')
                published = entry.get('published', str(datetime.now()))
                summary_raw = entry.get('summary', entry.get('description', ''))
                try: summary_clean = BeautifulSoup(summary_raw, "html.parser").get_text()[:300]
                except: summary_clean = summary_raw[:300] if summary_raw else ""
                articles.append({"source": source_name, "title": title, "link": link, "summary": summary_clean, "published": published})
        except Exception as e:
            continue
    return articles

def generate_infographic(prompt):
    """나노바나나 API 호출 (테스트용 랜덤 이미지 반환)"""
    # 실제 API 연동 시 이 부분을 수정하세요. 지금은 데모용입니다.
    try:
        # 실제로는 prompt를 API에 보내야 합니다.
        return f"https://picsum.photos/seed/{int(time.time())}/800/400"
    except:
        return None

def analyze_news_with_gemini(articles):
    """Gemini 모델 순차 시도 + 인포그래픽 프롬프트 생성"""
    if not articles: return None, None

    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "API 키 설정 오류", None

    # 1. 시도할 모델 목록 (안 되면 다음 걸로 자동 넘어감)
    candidate_models = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro',
        'gemini-pro',
        'gemini-1.0-pro'
    ]

    news_text = ""
    for idx, art in enumerate(articles):
        news_text += f"{idx+1}. [{art.get('source')}] {art.get('title')} : {art.get('summary')}\n"

    prompt = f"""
    너는 IT 뉴스 에디터야.
    1. 뉴스 브리핑: '📢 오늘의 핵심 흐름' (3줄 요약) 및 카테고리별 뉴스 정리 (마크다운)
    2. 인포그래픽 프롬프트: 이 내용을 시각화할 수 있는 영어 이미지 프롬프트 (한 줄)

    **반환 형식 (반드시 지켜줘):**
    (뉴스 브리핑 내용)
    ---구분선---
    (영어 이미지 프롬프트)

    [뉴스 목록]
    {news_text}
    """

    # 2. 모델 돌려막기 (Fallback Loop)
    last_error = ""
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            full_text = response.text
            
            # 성공하면 텍스트 나누기
            parts = full_text.split('---구분선---')
            briefing_text = parts[0].strip()
            image_url = None
            
            if len(parts) > 1:
                image_prompt = parts[1].strip()
                image_url = generate_infographic(image_prompt)
            
            return briefing_text, image_url
            
        except Exception as e:
            last_error = str(e)
            continue # 실패하면 다음 모델 시도

    return f"모든 AI 모델 연결 실패. 마지막 오류: {last_error}", None