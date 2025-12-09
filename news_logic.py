import feedparser
import google.generativeai as genai
from bs4 import BeautifulSoup
from datetime import datetime
import streamlit as st

def fetch_rss_feeds(feeds_list):
    """RSS 피드 목록에서 뉴스 수집 (변경 없음)"""
    articles = []
    if not feeds_list:
        return articles
    
    for feed in feeds_list:
        try:
            feed_url = feed.get('url', '')
            if not feed_url: continue
                
            parsed = feedparser.parse(feed_url)
            source_name = feed.get('name', 'Unknown Source')
            
            if not parsed.entries: continue
            
            for entry in parsed.entries[:5]:
                if not hasattr(entry, 'title') or not entry.title: continue
                if not hasattr(entry, 'link') or not entry.link: continue
                
                published = entry.get('published', str(datetime.now()))
                summary_raw = entry.get('summary', entry.get('description', ''))
                try:
                    summary_clean = BeautifulSoup(summary_raw, "html.parser").get_text()[:300]
                except:
                    summary_clean = summary_raw[:300] if summary_raw else ""
                
                articles.append({
                    "source": source_name,
                    "title": entry.title,
                    "link": entry.link,
                    "summary": summary_clean,
                    "published": published
                })
        except Exception as e:
            st.warning(f"RSS 수집 중 오류: {e}")
            continue
    
    return articles

def get_available_models(api_key):
    """현재 API 키로 사용 가능한 모델 목록을 확인합니다."""
    try:
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # models/ 접두사 제거하여 실제 모델명만 반환
                model_name = m.name.replace('models/', '')
                models.append(model_name)
        return models
    except:
        return []

def analyze_news_with_gemini(articles):
    """Gemini API 모델을 순차적으로 시도하는 폴백 로직"""
    if not articles:
        return "분석할 뉴스가 없습니다."

    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except KeyError:
        return "오류: GOOGLE_API_KEY가 secrets에 설정되지 않았습니다."

    # 1. 시도해볼 모델 목록 (사용 가능한 모델 기준으로 우선순위 설정)
    # 실제 API에서 확인된 사용 가능한 모델들
    candidate_models = [
        'gemini-2.5-flash',           # 최신 안정 버전
        'gemini-2.5-pro',             # 최신 Pro 버전
        'gemini-2.0-flash',           # 2.0 안정 버전
        'gemini-2.0-flash-001',       # 2.0 구체 버전
        'gemini-2.0-flash-exp',       # 2.0 실험 버전
        'gemini-flash-latest',        # 최신 Flash
        'gemini-pro-latest',          # 최신 Pro
        'gemini-2.5-flash-lite',      # 경량 버전
        'gemini-2.0-flash-lite'       # 경량 버전
    ]

    # 프롬프트 구성
    news_text = ""
    for idx, art in enumerate(articles):
        news_text += f"{idx+1}. [{art.get('source')}] {art.get('title')} : {art.get('summary')}\n"

    prompt = f"""
    너는 IT 전문 뉴스 에디터야. 아래 뉴스들을 바탕으로 '일일 IT 뉴스 브리핑'을 작성해줘.
    [요청사항]
    1. 헤드라인: '📢 오늘의 핵심 흐름' (3줄 요약)
    2. 카테고리별 뉴스 정리 (AI, 반도체, 모바일 등)
    3. 각 뉴스별 한 줄 요약과 원본 링크 포함
    4. 마크다운 형식으로 출력

    [뉴스 목록]
    {news_text}
    """

    # 2. 모델 하나씩 순서대로 시도 (Fallback Loop)
    last_error = ""
    
    for model_name in candidate_models:
        try:
            # 진행 상황을 UI에 살짝 표시 (디버깅용)
            print(f"Trying model: {model_name}...") 
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # 성공하면 바로 반환!
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            # 404(모델 없음)나 권한 오류면 다음 모델 시도
            if "404" in error_msg or "not found" in error_msg or "not supported" in error_msg:
                continue
            else:
                # 그 외 다른 에러면 그냥 다음 거 시도 (혹시 모르니)
                continue

    # 3. 모든 모델이 다 실패했을 때 - 사용 가능한 모델 목록 확인
    available_list = get_available_models(api_key)
    available_str = ', '.join(available_list[:10]) if available_list else '확인 불가 (API 키 문제 가능성)'
    
    return f"""
❌ 모든 AI 모델 연결에 실패했습니다.

**마지막 오류:** {last_error}

**💡 현재 API 키로 사용 가능한 모델 목록 (상위 10개):**
{available_str}

**🔧 해결 방법:**
위 목록에 있는 모델명 중 하나를 코드의 `candidate_models` 리스트에 추가해주세요.
"""