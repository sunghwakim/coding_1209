Cursor AI를 사용하여 개발하시기에 최적화된 구조로 설계해 드리겠습니다.

이 요구사항의 핵심은 **"데이터베이스 없이 GitHub 리포지토리 자체를 스토리지로 사용하는 것"**입니다. Streamlit Cloud는 앱이 재부팅되면 로컬 파일이 초기화되므로, 데이터(JSON)를 영구 저장하려면 GitHub API를 통해 리포지토리에 파일을 **Commit(업데이트)** 해야 합니다.

### 📁 프로젝트 구조
Cursor의 탐색기(Explorer)에 아래 파일들을 생성해주세요.

```
my-newsroom/
├── .streamlit/
│   └── secrets.toml      # (로컬용) API 키 저장소 (깃헙엔 업로드 X)
├── .gitignore           # Git 제외 파일 목록
├── data/                 # (초기 세팅용 폴더, 실제론 깃헙 리포지토리 파일 읽음)
│   ├── feeds.json        # RSS URL 목록
│   ├── news_data.json    # 분석된 뉴스 데이터
│   └── stats.json        # 방문자 통계
├── github_storage.py     # GitHub API 연동 모듈 (DB 역할)
├── news_logic.py         # RSS 파싱 및 Gemini 분석 로직
├── app.py                # 메인 Streamlit 앱
└── requirements.txt      # 라이브러리 목록
```

---

### 1. 라이브러리 설정 (`requirements.txt`)

```text
streamlit
feedparser
google-generativeai
PyGithub
beautifulsoup4
pandas
python-dateutil
```

### 2. GitHub 스토리지 모듈 (`github_storage.py`)
이 파일은 GitHub 리포지토리의 JSON 파일을 읽고 쓰는 DB 역할을 합니다.

```python
import json
import time
import streamlit as st
from github import Github, GithubException

# 캐싱을 사용하여 반복적인 API 호출 방지 (읽기 작업)
@st.cache_data(ttl=60)
def load_data_from_github(repo_name, file_path):
    """GitHub에서 JSON 파일을 읽어옵니다."""
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(repo_name)
        contents = repo.get_contents(file_path)
        return json.loads(contents.decoded_content.decode())
    except GithubException as e:
        # 파일이 없거나 접근 권한이 없는 경우
        if e.status == 404:
            return None
        st.warning(f"GitHub API 오류 (읽기): {e}")
        return None
    except KeyError:
        st.error("GITHUB_TOKEN이 secrets에 설정되지 않았습니다.")
        return None
    except Exception as e:
        st.warning(f"데이터 로드 중 오류 발생: {e}")
        return None

def save_data_to_github(repo_name, file_path, data, commit_message):
    """GitHub에 JSON 데이터를 저장(커밋)합니다."""
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(repo_name)
        
        # 데이터를 JSON 문자열로 변환
        json_content = json.dumps(data, indent=4, ensure_ascii=False)
        
        try:
            # 기존 파일이 있으면 업데이트 (SHA 필요)
            contents = repo.get_contents(file_path)
            repo.update_file(contents.path, commit_message, json_content, contents.sha)
        except GithubException as e:
            if e.status == 404:
                # 파일이 없으면 생성
                repo.create_file(file_path, commit_message, json_content)
            elif e.status == 403:
                # Rate limit 초과 시 대기
                st.warning("GitHub API rate limit에 도달했습니다. 잠시 후 다시 시도해주세요.")
                return False
            else:
                raise
        return True
    except KeyError:
        st.error("GITHUB_TOKEN이 secrets에 설정되지 않았습니다.")
        return False
    except GithubException as e:
        if e.status == 403:
            st.error("GitHub API 권한이 없거나 rate limit에 도달했습니다.")
        else:
            st.error(f"GitHub 저장 실패: {e}")
        return False
    except Exception as e:
        st.error(f"예상치 못한 오류 발생: {e}")
        return False
```

### 3. 뉴스 처리 & AI 로직 (`news_logic.py`)
RSS를 긁어오고 Gemini에게 요약을 요청하는 로직입니다.

```python
import feedparser
import google.generativeai as genai
from bs4 import BeautifulSoup
from datetime import datetime
import streamlit as st

def fetch_rss_feeds(feeds_list):
    """RSS 피드 목록에서 뉴스 수집"""
    articles = []
    
    if not feeds_list:
        return articles
    
    for feed in feeds_list:
        try:
            feed_url = feed.get('url', '')
            if not feed_url:
                continue
                
            parsed = feedparser.parse(feed_url)
            source_name = feed.get('name', 'Unknown Source')
            
            # RSS 파싱 오류 체크
            if parsed.bozo and parsed.bozo_exception:
                st.warning(f"RSS 피드 파싱 오류 ({source_name}): {parsed.bozo_exception}")
                continue
            
            if not parsed.entries:
                continue
            
            for entry in parsed.entries[:5]:  # 피드당 최신 5개만
                # 필수 필드 검증
                if not hasattr(entry, 'title') or not entry.title:
                    continue
                if not hasattr(entry, 'link') or not entry.link:
                    continue
                
                # 날짜 파싱
                published = entry.get('published', str(datetime.now()))
                
                # HTML 태그 제거
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
            st.warning(f"RSS 피드 수집 중 오류 발생 ({feed.get('name', 'Unknown')}): {e}")
            continue
    
    return articles

def analyze_news_with_gemini(articles):
    """Gemini API를 이용해 뉴스룸 리포트 생성"""
    if not articles:
        return "분석할 뉴스가 없습니다."

    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except KeyError:
        return "오류: GOOGLE_API_KEY가 secrets에 설정되지 않았습니다."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # 프롬프트 구성
        news_text = ""
        for idx, art in enumerate(articles):
            title = art.get('title', '제목 없음')
            source = art.get('source', '출처 없음')
            summary = art.get('summary', '요약 없음')
            news_text += f"{idx+1}. [{source}] {title} : {summary}\n"

        prompt = f"""
        너는 IT 전문 뉴스 에디터야. 아래 수집된 오늘자 IT 뉴스들을 바탕으로 '일일 IT 뉴스 브리핑'을 작성해줘.
        
        [요청사항]
        1. 전체적인 오늘의 IT 흐름을 3줄로 요약해줘 (헤드라인: '📢 오늘의 핵심 흐름').
        2. 뉴스들을 주제별(예: AI, 반도체, 모바일, 스타트업 등)로 카테고리화해서 정리해줘.
        3. 각 뉴스별로 한 줄 요약과 원본 링크를 포함해줘.
        4. 마크다운 형식으로 깔끔하게 출력해줘.

        [뉴스 목록]
        {news_text}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 분석 중 오류 발생: {str(e)}"
```

### 4. 메인 애플리케이션 (`app.py`)
UI와 전체 흐름을 제어합니다.

```python
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

    # 탭 3: AI 분석 실행
    with tab3:
        st.subheader("뉴스 수집 및 분석")
        st.write("등록된 RSS 피드에서 최신 뉴스를 가져와 Gemini로 분석합니다.")
        
        # RSS 피드 확인
        if not st.session_state.feeds:
            st.warning("⚠️ 등록된 RSS 피드가 없습니다. 'RSS 피드 관리' 탭에서 피드를 추가해주세요.")
        else:
            st.info(f"📡 현재 {len(st.session_state.feeds)}개의 RSS 피드가 등록되어 있습니다.")
        
        if st.button("🚀 분석 시작하기", disabled=not st.session_state.feeds):
            status_text = st.empty()
            progress_bar = st.progress(0)
            error_occurred = False
            
            try:
                # 1. 뉴스 수집
                status_text.text("RSS 피드 수집 중...")
                articles = fetch_rss_feeds(st.session_state.feeds)
                progress_bar.progress(30)
                
                if not articles:
                    st.warning("⚠️ 수집된 뉴스가 없습니다. RSS 피드 URL을 확인해주세요.")
                    progress_bar.empty()
                    status_text.empty()
                    error_occurred = True
                else:
                    st.success(f"✅ {len(articles)}개의 뉴스 기사를 수집했습니다.")
                    
                    # 2. AI 분석
                    status_text.text("Gemini AI가 분석 중입니다 (시간이 조금 걸립니다)...")
                    analysis_result = analyze_news_with_gemini(articles)
                    progress_bar.progress(70)
                    
                    # AI 분석 결과 검증
                    if analysis_result.startswith("오류") or analysis_result.startswith("AI 분석 중 오류"):
                        st.error(f"❌ {analysis_result}")
                        progress_bar.empty()
                        status_text.empty()
                        error_occurred = True
                    else:
                        # 3. 결과 저장
                        today_str = datetime.now().strftime('%Y-%m-%d')
                        st.session_state.news_report[today_str] = {
                            "updated_at": str(datetime.now()),
                            "content": analysis_result,
                            "article_count": len(articles)
                        }
                        
                        status_text.text("GitHub에 결과 저장 중...")
                        if save_data_to_github(REPO_NAME, "data/news_data.json", st.session_state.news_report, f"Update News {today_str}"):
                            progress_bar.progress(100)
                            status_text.empty()
                            st.success("✅ 분석 완료! '오늘의 브리핑' 메뉴에서 확인하세요.")
                            st.balloons()
                        else:
                            st.error("❌ GitHub 저장에 실패했습니다. 다시 시도해주세요.")
                            error_occurred = True
                            
            except Exception as e:
                st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")
                progress_bar.empty()
                status_text.empty()
                error_occurred = True
            
            if error_occurred:
                progress_bar.empty()
                status_text.empty()
```

---

### 5. 배포 및 설정 방법 (매우 중요)

Cursor AI로 코드를 작성한 후, 아래 절차를 따라야 정상 작동합니다.

#### 1단계: GitHub 리포지토리 준비
1.  GitHub에 새 리포지토리를 만듭니다 (예: `my-newsroom`).
2.  `data` 폴더를 만들고 그 안에 빈 JSON 파일(`feeds.json`, `news_data.json`, `stats.json`)을 만들어 올려두세요 (빈 리스트 `[]` 나 빈 객체 `{}` 내용으로).
    *   *팁: 로컬에서 위 코드로 `data` 폴더 만들고 `[]`만 넣은 뒤 푸시하세요.*
3.  `.gitignore` 파일을 생성하여 민감한 정보가 커밋되지 않도록 합니다 (아래 참고).

#### 2단계: GitHub Personal Access Token 발급
1.  GitHub Settings -> Developer settings -> Personal access tokens -> Tokens (classic)
2.  **Generate new token** 클릭.
3.  **Scopes**에서 `repo` (전체 권한)를 체크합니다.
4.  생성된 토큰(`ghp_...`)을 복사해 둡니다.

#### 3단계: Streamlit Cloud 배포 설정
1.  GitHub에 위 코드들을 모두 Push 합니다.
2.  Streamlit Cloud에 접속해서 해당 리포지토리를 배포합니다.
3.  **Advanced Settings (Secrets)** 에 들어가서 아래 내용을 붙여넣습니다.

```toml
GOOGLE_API_KEY = "여기에_구글_GEMINI_키"
GITHUB_TOKEN = "여기에_위에서_만든_GITHUB_토큰"
REPO_NAME = "당신의깃헙아이디/리포지토리이름" 
# 예: REPO_NAME = "honggildong/my-newsroom"
```

### 6. .gitignore 파일

민감한 정보가 GitHub에 커밋되지 않도록 `.gitignore` 파일을 생성하세요.

```text
# Streamlit secrets
.streamlit/secrets.toml

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

---

### ✨ Cursor AI 활용 팁
이 코드를 Cursor AI에 복사해 넣은 후, **Composer (Ctrl+I)** 기능을 열고 이렇게 요청해보세요:

> "현재 프로젝트 구조에서 `news_logic.py`의 `fetch_rss_feeds` 함수를 수정해서, 오늘 날짜(`datetime.now()`)와 일치하는 뉴스만 필터링하도록 코드를 고쳐줘."

또는

> "대시보드의 통계 그래프를 pandas를 사용해서 날짜별 방문자 추이 라인 차트로 시각화하는 코드를 추가해줘."

이렇게 하면 기본 뼈대 위에 원하는 기능을 쉽게 확장할 수 있습니다.