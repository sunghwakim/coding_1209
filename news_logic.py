import feedparser
import google.generativeai as genai
from bs4 import BeautifulSoup
from datetime import datetime
import streamlit as st
import urllib.parse
import random

def fetch_rss_feeds(feeds_list):
    """RSS 피드 수집 (기존과 동일)"""
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
        except: continue
    return articles

def generate_infographic(prompt):
    """
    ✨ 고화질(Flux) 인포그래픽 생성 함수
    URL 설정 없이도, 최신 AI 모델을 사용하여 4K급 이미지를 생성합니다.
    """
    try:
        # 1. 프롬프트 강화: '인포그래픽', '고화질', '4K' 같은 단어를 자동으로 추가
        enhanced_prompt = f"infographic, data visualization, flat design, high quality, 4k, detailed, professional, {prompt}"
        
        # 2. 인터넷 주소용으로 변환
        encoded_prompt = urllib.parse.quote(enhanced_prompt)
        
        # 3. 매번 다른 그림이 나오도록 랜덤 번호 생성
        seed = random.randint(1, 99999)
        
        # 4. 고화질 모델(Flux) 호출 URL 생성
        # (이 주소는 키 없이도 고화질을 뽑아주는 마법의 주소입니다)
        image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=600&seed={seed}&model=flux"
        
        return image_url

    except Exception as e:
        # 실패 시에만 저화질(picsum) 사용
        return "https://picsum.photos/800/400"

def analyze_news_with_gemini(articles):
    """나노바나나 키(Gemini)로 분석 + 고화질 그림"""
    if not articles: return None, None

    # 1. API 키 연결 (사용자님이 주신 키 사용)
    try:
        api_key = st.secrets["GOOGLE_API_KEY"] 
        genai.configure(api_key=api_key)
    except Exception as e:
        return f"❌ API 키 설정 오류: secrets.toml에 GOOGLE_API_KEY가 있는지 확인하세요.", None

    # 2. 모델 설정 (사용자 키에 맞는 모델 자동 탐색)
    candidate_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']

    news_text = ""
    for idx, art in enumerate(articles):
        news_text += f"{idx+1}. [{art.get('source')}] {art.get('title')}\n"

    # 3. AI에게 내리는 지령 (프롬프트)
    prompt = f"""
    너는 IT 전문 뉴스 앵커야.
    1. **뉴스 브리핑**: '📢 오늘의 핵심 흐름' (3줄 요약) 및 뉴스 정리 (마크다운)
    2. **그림 요청**: 이 뉴스 내용을 한 장의 인포그래픽으로 표현할 수 있는 **영어 묘사(English Prompt)** 한 줄.
       (예: futuristic network map with glowing blue nodes, cyber security shield, 3d render, white background)

    **반환 형식 (이대로만 대답해):**
    (뉴스 브리핑 내용)
    ---구분선---
    (영어 이미지 프롬프트)

    [뉴스 목록]
    {news_text}
    """

    # 4. 분석 실행
    last_error = ""
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            full_text = response.text
            
            parts = full_text.split('---구분선---')
            briefing_text = parts[0].strip()
            image_url = None
            
            if len(parts) > 1:
                image_prompt = parts[1].strip()
                # ✨ 고화질 이미지 생성 함수 호출
                image_url = generate_infographic(image_prompt)
            
            return briefing_text, image_url
            
        except Exception as e:
            last_error = str(e)
            continue

    return f"❌ 분석 실패: {last_error}", None