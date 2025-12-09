# Gemini API 오류 리포트

## 🔴 오류 정보

**오류 메시지:**
```
404 models/gemini-pro is not found for API version v1beta, or is not supported for generateContent. 
Call ListModels to see the list of available models and their supported methods.
```

**발생 위치:** `news_logic.py` - `analyze_news_with_gemini()` 함수

**오류 코드:** 404 Not Found

**발생 빈도:** 반복 발생

---

## 🔍 원인 분석

### 1. 모델명 불일치
- **코드에서 사용:** `gemini-1.5-flash`
- **오류 메시지:** `models/gemini-pro`
- **가능성:** API가 내부적으로 다른 모델명을 사용하거나, 모델명이 변경되었을 수 있음

### 2. API 버전 문제
- 오류 메시지에 `API version v1beta` 언급
- 최신 `google-generativeai` 라이브러리는 `v1` API를 사용해야 할 수 있음

### 3. 모델 사용 불가
- 해당 모델이 현재 API 키로 사용 불가능할 수 있음
- API 키의 권한 또는 리전 제한 가능성

### 4. 라이브러리 버전 문제
- `google-generativeai` 패키지 버전이 오래되었을 수 있음
- 최신 버전으로 업데이트 필요

---

## 🛠️ 해결 방안

### 방안 1: 사용 가능한 모델 확인 및 변경
1. 사용 가능한 모델 목록 확인
2. 지원되는 모델명으로 변경
3. 권장 모델: `gemini-pro`, `gemini-1.5-pro`, `gemini-1.5-flash-latest`

### 방안 2: API 버전 명시
- API 버전을 명시적으로 설정
- `v1beta` 대신 `v1` 사용

### 방안 3: 에러 핸들링 개선
- 더 구체적인 에러 메시지 제공
- 사용 가능한 모델 목록 자동 확인 기능 추가
- 폴백 모델 사용 로직 추가

### 방안 4: 라이브러리 업데이트
- `google-generativeai` 패키지를 최신 버전으로 업데이트

---

## 📝 권장 수정 사항

1. **모델명 변경:** `gemini-1.5-flash` → `gemini-1.5-flash-latest` 또는 `gemini-pro`
2. **에러 핸들링 강화:** 구체적인 에러 메시지 및 모델 목록 확인
3. **폴백 로직 추가:** 첫 번째 모델 실패 시 대체 모델 시도
4. **API 버전 명시:** 필요시 API 버전 설정

---

## ✅ 적용된 수정 사항

### 1. 폴백 모델 로직 추가
- 여러 모델명을 순차적으로 시도하는 로직 구현
- 모델 우선순위:
  1. `gemini-1.5-flash-latest`
  2. `gemini-1.5-flash`
  3. `gemini-1.5-pro-latest`
  4. `gemini-1.5-pro`
  5. `gemini-pro`
  6. 기타 최신 모델들

### 2. 사용 가능한 모델 자동 확인
- `get_available_models()` 함수 추가
- 실패 시 사용 가능한 모델 목록을 에러 메시지에 표시

### 3. 에러 핸들링 개선
- 구체적인 에러 메시지 제공
- 404 오류와 다른 오류 구분 처리
- 사용 가능한 모델 목록 표시

### 4. 라이브러리 버전 명시
- `requirements.txt`에 `google-generativeai>=0.3.0` 명시

---

## 🔧 테스트 필요 사항

- [x] 사용 가능한 모델 목록 확인 함수 추가
- [x] 폴백 로직 구현
- [x] 에러 핸들링 개선
- [x] 라이브러리 버전 명시
- [ ] 실제 API 테스트
- [ ] 각 모델명으로 테스트
- [ ] API 키 권한 확인

---

## 📋 수정된 파일

1. `news_logic.py` - 폴백 모델 로직 및 에러 핸들링 개선
2. `requirements.txt` - 라이브러리 버전 명시

---

## 📅 작성일
2024-12-09

## 🔄 수정일
2024-12-09

