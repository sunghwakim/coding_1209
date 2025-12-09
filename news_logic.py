import feedparser
import google.generativeai as genai
from bs4 import BeautifulSoup
from datetime import datetime
import streamlit as st
import requests  # API 호출용 라이브러리
import time
import json

def fetch_rss_feeds(feeds_list):
    """RSS 피드 목록에서 뉴스 수집 (기존과 동일)"""
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

# === 🍌 나노바나나 API 호출 함수 (여기가 핵심!) ===
def generate_infographic(prompt):
    """나노바나나 Pro API를 호출하여 이미지를 생성합니다."""
    try:
        # 1. Secrets에서 키 가져오기
        api_key = st.secrets.get("NANOBANA_API_KEY", "")
        if not api_key:
            print("⚠️ NANOBANA_API_KEY가 없습니다.")
            return None

        # ==========================================================
        # 🚨 [사용자 설정 필요] 나노바나나 API 문서에 맞춰 수정해주세요!
        # ==========================================================
        
        # (1) API 주소 (Endpoint)
        # 예: "https://api.nanobana.com/v1/generate" 혹은 제공받은 URL
        api_url = "https://api.nanobana.com/v1/generate" 

        # (2) 보낼 데이터 (Payload)
        # 나노바나나가 요구하는 형식(JSON)을 맞춰야 합니다.
        payload = {
            "prompt": f"Infographic style, high quality, {prompt}", # 프롬프트
            "model": "pro-v1",        # Pro 모델 이름 (문서 확인 필요)
            "width": 1024,
            "height": 1024,
            "negative_prompt": "text, watermark, blurry, low quality"
        }

        # (3) 헤더 (인증 정보)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # ==========================================================

        print(f"🎨 나노바나나에게 요청 중... 프롬프트: {prompt[:30]}...")
        
        # 2. 실제 요청 보내기 (POST)
        response = requests.post(api_url, json=payload, headers=headers)
        
        # 3. 응답 처리
        if response.status_code == 200:
            result = response.json()
            # 🚨 중요: 응답에서 이미지 주소가 어디에 들어있는지 확인해야 합니다.
            # 보통 result['url'], result['data'][0]['url'], result['image'] 중 하나입니다.
            image_url = result.get('url') # 예시 (맞게 수정하세요)
            
            # 만약 url이 리스트 안에 있다면:
            # image_url = result['data'][0]['url']
            
            return image_url
        else:
            print(f"❌ API 오류 ({response.status_code}): {response.text}")
            return None

    except Exception as e:
        print(f"❌ 이미지 생성 중 예외 발생: {e}")
        return None


def analyze_news_with_gemini(articles):
    """Gemini 모델 순차 시도 + 인포그래픽 프롬프트"""
    if not articles: return None, None

    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except:
        return "API 키 설정 오류. Secrets를 확인하세요.", None

    # 1. 확실한 모델 목록
    candidate_models = [
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-pro'
    ]

    news_text = ""
    for idx, art in enumerate(articles):
        news_text += f"{idx+1}. [{art.get('source')}] {art.get('title')}\n"

    prompt = f"""
    너는 IT 뉴스 에디터이자 인포그래픽 기획자야.
    1. 뉴스 브리핑: '📢 오늘의 핵심 흐름' (3줄 요약) 및 뉴스 정리 (마크다운)
    2. 인포그래픽 프롬프트: 이 뉴스 내용을 한장의 인포그래픽으로 표현할 수 있는 **영어 묘사(English Prompt)**. 
       (예: futuristic chart, data visualization, glowing nodes, cyber style)

    **반환 형식 (반드시 지켜줘):**
    (뉴스 브리핑 내용)
    ---구분선---
    (영어 이미지 프롬프트)

    [뉴스 목록]
    {news_text}
    """

    # 2. 모델 돌려막기
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
                # 나노바나나 호출!
                image_url = generate_infographic(image_prompt)
            
            return briefing_text, image_url
            
        except Exception as e:
            last_error = str(e)
            continue

    return f"모든 모델 연결 실패.\n마지막 오류: {last_error}", None