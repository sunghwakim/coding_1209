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

