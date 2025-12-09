import streamlit as st
import pandas as pd
from datetime import datetime
from github_storage import load_data_from_github, save_data_to_github
from news_logic import fetch_rss_feeds, analyze_news_with_gemini

# --- 설정 ---
st.set_page_config(page_title="My AI Newsroom", layout="wide", page_icon="📰")

# GitHub 리포지토리 정보 (secrets에서 가져옴)
try:
    REPO_NAME = st.secrets["REPO_NAME"] # 예: "username/repo-name"
except:
    st.error("Secrets에 REPO_NAME을 설정해주세요.")
    st.stop()

# --- 데이터 초기화 (GitHub에서 로드) ---
if 'feeds' not in st.session_state:
    data = load_data_from_github(REPO_NAME, "data/feeds.json")
    st.session_state.feeds = data if data else [{"name": "Google News IT", "url": "https://news.google.com/rss/search?q=IT&hl=ko&gl=KR&ceid=KR%3Ako"}]

if 'news_report' not in st.session_state:
    data = load_data_from_github(REPO_NAME, "data/news_data.json")
    st.session_state.news_report = data if data else {}

if 'stats' not in st.session_state:
    data = load_data_from_github(REPO_NAME, "data/stats.json")
    st.session_state.stats = data if data else {"visits": 0, "last_updated": ""}

def load_feeds():
    """세션에 저장된 피드 목록을 반환합니다."""
    return st.session_state.get('feeds', [])

# --- 방문자 카운트 (새 세션일 때만 증가 로직 - 간소화 버전) ---
# 주의: Streamlit은 리로드마다 실행되므로 실제 배포 시엔 Session ID 체크 등 정교한 로직 필요
# 여기서는 대시보드에서 '통계 업데이트' 버튼을 누를 때 저장하는 방식으로 구현하여 API 호출 절약

# --- UI 구성 ---
st.sidebar.title("📰 나만의 뉴스룸")
menu = st.sidebar.radio("메뉴 이동", ["오늘의 브리핑", "대시보드 (관리자)"])

# 1. 메인 화면: 오늘의 브리핑
if menu == "오늘의 브리핑":
    st.title("☕ 오늘의 IT 뉴스 브리핑")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # 오늘자 리포트가 있는지 확인
    if today_str in st.session_state.news_report:
        report_data = st.session_state.news_report[today_str]
        st.markdown(f"**업데이트 시간:** {report_data['updated_at']}")
        st.divider()
        st.markdown(report_data['content'])
    else:
        st.info("아직 오늘의 뉴스 브리핑이 생성되지 않았습니다. 대시보드에서 분석을 실행해주세요.")
        
    # 방문자 수 살짝 보여주기
    st.sidebar.divider()
    st.sidebar.caption(f"Total Visits: {st.session_state.stats.get('visits', 0)}")


# 2. 대시보드: 관리 기능
elif menu == "대시보드 (관리자)":
    st.title("🛠️ 관리자 대시보드")
    
    tab1, tab2, tab3 = st.tabs(["📊 통계", "📡 RSS 피드 관리", "🤖 AI 분석 실행"])
    
    # 탭 1: 통계
    with tab1:
        st.subheader("접속자 통계")
        current_visits = st.session_state.stats.get('visits', 0)
        st.metric("총 방문 횟수", current_visits)
        
        # 간단한 카운트 증가 테스트 버튼 (DB 쓰기 테스트용)
        if st.button("방문자 수 +1 (DB 테스트)"):
            st.session_state.stats['visits'] = current_visits + 1
            st.session_state.stats['last_updated'] = str(datetime.now())
            if save_data_to_github(REPO_NAME, "data/stats.json", st.session_state.stats, "Update stats"):
                st.success("통계가 GitHub에 저장되었습니다!")
                st.rerun()

    # 탭 2: RSS 관리
    with tab2:
        st.subheader("등록된 RSS 피드")
        
        # 리스트 출력
        if st.session_state.feeds:
            df_feeds = pd.DataFrame(st.session_state.feeds)
            st.dataframe(df_feeds, use_container_width=True)
            
            # 삭제 기능
            feed_to_remove = st.selectbox("삭제할 피드 선택", [f['name'] for f in st.session_state.feeds])
            if st.button("선택한 피드 삭제"):
                st.session_state.feeds = [f for f in st.session_state.feeds if f['name'] != feed_to_remove]
                save_data_to_github(REPO_NAME, "data/feeds.json", st.session_state.feeds, "Remove RSS Feed")
                st.success("삭제되었습니다!")
                st.rerun()
        
        st.divider()
        st.subheader("새 피드 추가")
        with st.form("add_feed_form"):
            new_name = st.text_input("언론사/블로그 이름")
            new_url = st.text_input("RSS URL")
            submitted = st.form_submit_button("추가하기")
            
            if submitted and new_name and new_url:
                new_feed = {"name": new_name, "url": new_url}
                st.session_state.feeds.append(new_feed)
                save_data_to_github(REPO_NAME, "data/feeds.json", st.session_state.feeds, "Add RSS Feed")
                st.success("추가되었습니다!")
                st.rerun()

    # 탭 3: AI 분석 실행 (인포그래픽 생성 포함)
    with tab3:
        st.subheader("🤖 AI 뉴스 분석 및 인포그래픽")
        start_analysis_btn = st.button("🚀 분석 및 이미지 생성 시작하기")

        if start_analysis_btn:
            # 1. 뉴스 수집
            with st.spinner('📰 최신 뉴스를 수집하고 있습니다...'):
                feeds = load_feeds()
                articles = fetch_rss_feeds(feeds)
            
            if not articles:
                st.error("수집된 뉴스가 없습니다. RSS 피드를 확인해주세요.")
            else:
                st.success(f"✅ {len(articles)}개의 뉴스 기사를 수집했습니다.")
                
                # 2. AI 분석 및 이미지 생성
                with st.spinner('🧠 Gemini가 분석하고 나노바나나가 그리는 중... (시간이 좀 걸립니다)'):
                    briefing_text, image_url = analyze_news_with_gemini(articles)

                if image_url:
                    # 3. 인포그래픽 이미지 표시
                    st.markdown("### 📊 오늘의 인포그래픽")
                    st.image(image_url, caption="AI가 생성한 뉴스 인포그래픽", use_column_width=True)
                    st.divider()

                if briefing_text and not briefing_text.startswith("분석 중 오류"):
                    # 4. 뉴스 요약문 표시
                    st.markdown(briefing_text)
                    st.balloons()
                elif briefing_text:
                    st.error(briefing_text)

