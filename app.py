import streamlit as st
import pandas as pd
from datetime import datetime
from github_storage import load_data_from_github, save_data_to_github
from news_logic import fetch_rss_feeds, analyze_news_with_gemini

# --- 설정 ---
st.set_page_config(page_title="My AI Newsroom", layout="wide", page_icon="📰")

# GitHub 리포지토리 정보 로드
try:
    REPO_NAME = st.secrets["REPO_NAME"]
except:
    st.error("Secrets에 REPO_NAME을 설정해주세요.")
    st.stop()

# --- 데이터 초기화 ---
if 'feeds' not in st.session_state:
    data = load_data_from_github(REPO_NAME, "data/feeds.json")
    st.session_state.feeds = data if data else [{"name": "Google News IT", "url": "https://news.google.com/rss/search?q=IT&hl=ko&gl=KR&ceid=KR%3Ako"}]

if 'news_report' not in st.session_state:
    data = load_data_from_github(REPO_NAME, "data/news_data.json")
    st.session_state.news_report = data if data else {}

if 'stats' not in st.session_state:
    data = load_data_from_github(REPO_NAME, "data/stats.json")
    st.session_state.stats = data if data else {"visits": 0, "last_updated": ""}

# --- UI 구성 ---
st.sidebar.title("📰 나만의 뉴스룸")
menu = st.sidebar.radio("메뉴 이동", ["오늘의 브리핑", "대시보드 (관리자)"])

# 1. 메인 화면: 오늘의 브리핑 (수정됨: 이미지 표시 기능 추가!)
if menu == "오늘의 브리핑":
    st.title("☕ 오늘의 IT 뉴스 브리핑")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # 오늘자 리포트가 있는지 확인
    if today_str in st.session_state.news_report:
        report_data = st.session_state.news_report[today_str]
        
        st.caption(f"Update: {report_data['updated_at']} | 기사 {report_data.get('article_count', 0)}개 분석")
        st.divider()
        
        # 🖼️ [NEW] 저장된 인포그래픽 이미지가 있으면 보여주기
        if report_data.get('image_url'):
            st.image(report_data['image_url'], caption="Today's AI Infographic", use_container_width=True)
            st.divider()

        st.markdown(report_data['content'])
    else:
        st.info("아직 오늘의 뉴스 브리핑이 생성되지 않았습니다. 관리자 대시보드에서 분석을 실행해주세요.")
        
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
        
        if st.button("방문자 수 +1 (DB 테스트)"):
            st.session_state.stats['visits'] = current_visits + 1
            st.session_state.stats['last_updated'] = str(datetime.now())
            if save_data_to_github(REPO_NAME, "data/stats.json", st.session_state.stats, "Update stats"):
                st.success("통계가 GitHub에 저장되었습니다!")
                st.rerun()

    # 탭 2: RSS 관리
    with tab2:
        st.subheader("등록된 RSS 피드")
        if st.session_state.feeds:
            df_feeds = pd.DataFrame(st.session_state.feeds)
            st.dataframe(df_feeds, use_container_width=True)
            
            feed_to_remove = st.selectbox("삭제할 피드 선택", [f['name'] for f in st.session_state.feeds])
            if st.button("선택한 피드 삭제"):
                st.session_state.feeds = [f for f in st.session_state.feeds if f['name'] != feed_to_remove]
                save_data_to_github(REPO_NAME, "data/feeds.json", st.session_state.feeds, "Remove RSS Feed")
                st.success("삭제되었습니다!")
                st.rerun()
        
        st.divider()
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

    # 탭 3: AI 분석 실행 (수정됨: 이미지 URL 저장 로직 추가!)
    with tab3:
        st.subheader("뉴스 수집 및 분석")
        
        if st.button("🚀 분석 및 이미지 생성 시작하기", disabled=not st.session_state.feeds):
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            try:
                # 1. 뉴스 수집
                status_text.text("RSS 피드 수집 중...")
                articles = fetch_rss_feeds(st.session_state.feeds)
                progress_bar.progress(30)
                
                if not articles:
                    st.error("수집된 뉴스가 없습니다.")
                else:
                    # 2. AI 분석
                    status_text.text("Gemini와 Nanobana가 열심히 작업 중입니다...")
                    briefing_text, image_url = analyze_news_with_gemini(articles)
                    progress_bar.progress(70)
                    
                    if briefing_text and not briefing_text.startswith("모든 모델"):
                        # 3. 결과 저장 (이미지 URL 포함!)
                        today_str = datetime.now().strftime('%Y-%m-%d')
                        st.session_state.news_report[today_str] = {
                            "updated_at": str(datetime.now()),
                            "content": briefing_text,
                            "image_url": image_url,  # 👈 여기가 핵심! 이미지를 저장합니다.
                            "article_count": len(articles)
                        }
                        
                        status_text.text("GitHub에 결과 저장 중...")
                        if save_data_to_github(REPO_NAME, "data/news_data.json", st.session_state.news_report, f"Update News {today_str}"):
                            progress_bar.progress(100)
                            status_text.empty()
                            st.success("✅ 분석 완료! '오늘의 브리핑' 메뉴에서 확인하세요.")
                            st.balloons()
                            
                            # 미리보기
                            if image_url:
                                st.image(image_url, caption="생성된 인포그래픽")
                            st.markdown(briefing_text)
                        else:
                            st.error("저장 실패")
                    else:
                        st.error(f"분석 실패: {briefing_text}")
                        
            except Exception as e:
                st.error(f"오류 발생: {e}")