import feedparser
import google.generativeai as genai
from bs4 import BeautifulSoup
from datetime import datetime
import streamlit as st
import urllib.parse # 주소 변환 도구
import random

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

# === 🎨 [핵심] 무료 인포그래픽 생성 함수 (설정 불필요!) ===
def generate_infographic(prompt):
    """
    복잡한 API 키나 URL 설정 없이,
    Pollinations AI를 통해 즉시 고퀄리티 이미지를 생성합니다.
    """
    try:
        # 1. 프롬프트를 인터넷 주소용으로 이쁘게 포장
        # 'infographic', 'vector art' 같은 스타일 단어를 강제로 추가해서 퀄리티를 높입니다.
        enhanced_prompt = f"infographic, data visualization, flat design, high quality, {prompt}"
        encoded_prompt = urllib.parse.quote(enhanced_prompt)
        
        # 2. 랜덤 숫자를 넣어 매번 새로운 그림이 나오게 함
        seed = random.randint(1, 99999)
        
        # 3. 마법의 주소 생성 (여기로 접속하면 그림이 뚝딱!)
        image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=600&seed={seed}&model=flux"
        
        return image_url

    except Exception as e:
        # 만약 실패하면 예비용 이미지를 보여줌
        return "https://picsum.photos/800/400"

def analyze_news_with_gemini(articles):
    """Gemini로 분석하고 + 무료 AI로 그리기"""
    if not articles: return None, None

    try:
        # secrets.toml에 넣은 구글 키를 가져옵니다
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "API 키 설정 오류. secrets.toml을 확인해주세요.", None

    # 사용할 모델 후보 (최신 순)
    candidate_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']

    news_text = ""
    for idx, art in enumerate(articles):
        news_text += f"{idx+1}. [{art.get('source')}] {art.get('title')}\n"

    # AI에게 내리는 지령 (프롬프트)
    prompt = f"""
    너는 IT 전문 뉴스 앵커야.
    1. **뉴스 브리핑**: '📢 오늘의 핵심 흐름' (3줄 요약) 및 뉴스 정리 (마크다운)
    2. **그림 요청**: 이 뉴스 내용을 한 장의 인포그래픽으로 표현할 수 있는 **영어 묘사(English Prompt)** 한 줄.
       (예: futuristic network map with glowing blue nodes, cyber security shield, 3d render)

    **반환 형식 (이대로만 대답해):**
    (뉴스 브리핑 내용)
    ---구분선---
    (영어 이미지 프롬프트)

    [뉴스 목록]
    {news_text}
    """

    # 모델이 안 되면 다음 모델로 넘어가며 시도
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
                # ✨ 위에서 만든 무료 이미지 함수 호출!
                image_url = generate_infographic(image_prompt)
            
            return briefing_text, image_url
            
        except Exception as e:
            continue

    return "분석 실패: 구글 API 키를 확인해주세요.", None