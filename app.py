import streamlit as st
import google.generativeai as genai
from PIL import Image
import time

# ==========================================
# 1. 화면 기본 설정
# ==========================================
st.set_page_config(page_title="부동산 블로그 작가", page_icon="✍️")
st.title("✍️ 부동산 블로그 상세 글쓰기")
st.caption("사진만 넣으면 AI가 네이버 블로그 글을 써줍니다! (최적 모델 자동 탐색 📡)")

# ==========================================
# 2. API 키 처리
# ==========================================
api_key = None
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
except:
    pass

if not api_key:
    api_key = st.text_input("🔑 구글 API 키를 입력하세요:", type="password")

# ==========================================
# 3. [핵심] 오뚝이 함수
# ==========================================
def generate_content_with_retry(model, prompt, image=None):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if image:
                return model.generate_content([prompt, image])
            else:
                return model.generate_content(prompt)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                wait_time = 20
                st.warning(f"⚠️ 사용량이 몰려서 20초만 쉬었다가 다시 할게요... (시도 {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                raise e
    raise Exception("죄송합니다. AI가 응답하지 않습니다.")

# ==========================================
# 4. 메인 기능
# ==========================================
if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # -----------------------------------------------------------
        # 🔥 [필살기] 되는 모델 찾을 때까지 하나씩 다 찔러보기
        # -----------------------------------------------------------
        
        # 우리가 시도해볼 후보군 (위에서부터 순서대로 시도함)
        # 2.5(제한걸린거)는 아예 뺐습니다.
        candidate_models = [
            "gemini-1.5-flash-001",    # 가장 호환성 좋음
            "gemini-1.5-flash-002",    # 최신
            "gemini-1.5-flash-latest", # 일반
            "gemini-1.5-flash",        # 일반
            "gemini-1.5-flash-8b",     # 가벼운 무료 버전
            "gemini-2.0-flash-exp",    # 2.0 실험버전 (무료, 제한 넉넉함)
        ]
        
        final_model_name = None
        
        # 1. 후보군 중에서 내 키로 '접속 가능한' 놈 찾기
        # (실제 목록과 대조)
        my_available_models = [m.name.replace("models/", "") for m in genai.list_models()]
        
        for candidate in candidate_models:
            if candidate in my_available_models:
                final_model_name = candidate
                break
        
        # 2. 만약 목록 매칭으로 못 찾았으면, 그냥 2.0-exp라도 강제 할당
        if not final_model_name:
             # 목록에 없더라도 강제로 시도해볼만한 녀석
             final_model_name = "gemini-1.5-flash-001" 

        # 모델 연결
        model = genai.GenerativeModel(final_model_name)
        
        # ✅ [확인용] 화면에 어떤 모델 잡혔는지 작게 보여줌 (성공하면 나중에 지워도 됨)
        st.success(f"✅ 연결 성공! 사용 중인 모델: {final_model_name}")
            
    except Exception as e:
        st.error(f"키 설정 오류: {e}")

    st.divider()
    
    # --- 정보 입력 칸 ---
    st.header("1. 매물 기본 정보")
    col1, col2 = st.columns(2)
    with col1:
        price = st.text_input("💰 가격", placeholder="예: 매매 5억 / 전세 3억")
        location = st.text_input("📍 위치/아파트명", placeholder="예: 수성구 롯데캐슬")
    with col2:
        features = st.text_area("✨ 특징 (전체적인 장점)", placeholder="예: 남향, 올수리, 학군 좋음, 입주협의", height=100)

    # --- 사진 올리는 칸 ---
    st.header("2. 사진 업로드 (여러 장 가능!)")
    uploaded_files = st.file_uploader(
        "블로그 순서대로 사진을 드래그해서 넣어주세요", 
        type=["jpg", "jpeg", "png", "webp"], 
        accept_multiple_files=True
    )

    # --- 실행 버튼 ---
    st.divider()
    if uploaded_files and st.button("🚀 블로그 포스팅 시작하기 (클릭)"):
        
        # 1️⃣ 서론(인트로) 작성
        with st.spinner("1단계: 매력적인 제목과 인사말을 쓰는 중..."):
            intro_prompt = f"""
            당신은 베테랑 공인중개사 블로거입니다.
            아래 정보를 바탕으로 네이버 블로그 '도입부(서론)'를 작성해주세요.
            
            [정보]
            - 위치: {location}
            - 가격: {price}
            - 특징: {features}
            
            [요청사항]
            1. 클릭을 부르는 매력적인 제목 3가지를 추천해주세요.
            2. 날씨나 계절감 있는 다정한 인사말로 시작하세요.
            3. 매물의 핵심 정보를 요약해서 기대감을 주세요.
            4. 아직 사진 묘사는 하지 마세요.
            """
            
            try:
                intro_res = generate_content_with_retry(model, intro_prompt)
                st.success("✅ 도입부 작성 완료!")
                st.subheader("📝 [1] 제목 및 인사말")
                st.text_area("도입부 복사하기", value=intro_res.text, height=200)
            except Exception as e:
                st.error(f"글쓰기 실패 ({final_model_name}): {e}")

        st.divider()

        # 2️⃣ 사진별 본문 작성 (반복문)
        st.subheader("📝 [2] 사진별 상세 설명")
        st.info("👇 사진 순서대로 글이 생성됩니다. 사진 밑에 글을 복사해서 쓰세요!")

        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            status_text = st.empty()
            status_text.caption(f"📸 {i+1}번째 사진 분석 중...")

            try:
                image = Image.open(file)
                
                img_prompt = f"""
                이 사진은 {location} 부동산 매물의 내부 사진 중 하나입니다.
                이 사진을 보고 블로그 본문 내용을 3~4줄 정도로 자연스럽게 작성해주세요.
                
                [요청사항]
                1. '거실', '주방', '안방', '화장실', '현관' 중 어디인지 파악하세요.
                2. 사진에 보이는 장점(넓음, 깨끗함, 채광, 수납공간 등)을 구체적으로 칭찬하세요.
                3. 아주 친절한 '해요체'를 쓰세요. (예: "보시다시피 거실이 정말 넓게 빠졌어요~")
                """
                
                response = generate_content_with_retry(model, img_prompt, image)
                
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.image(image, use_container_width=True)
                with c2:
                    st.text_area(f"{i+1}번째 사진 설명", value=response.text, height=150)
                
                status_text.caption(f"✅ {i+1}번째 사진 완료!")
                
            except Exception as e:
                st.error(f"{i+1}번째 사진 처리 실패: {e}")

            progress_bar.progress((i + 1) / len(uploaded_files))
            time.sleep(5)

        st.divider()

        # 3️⃣ 결론(아웃트로) 작성
        with st.spinner("3단계: 마무리 인사와 태그 작성 중..."):
            try:
                outro_prompt = f"""
                블로그 포스팅을 마무리하는 '결론' 부분을 작성해주세요.
                
                [정보]
                - 위치: {location}
                
                [요청사항]
                1. 언제든 문의 달라는 신뢰감 있는 멘트.
                2. "모바일에서 터치하시면 바로 전화 연결됩니다" 문구 포함.
                3. 검색 잘 되는 해시태그 10개 추천.
                """
                outro_res = generate_content_with_retry(model, outro_prompt)
                
                st.subheader("📝 [3] 마무리 및 해시태그")
                st.text_area("마무리 복사하기", value=outro_res.text, height=200)
                st.success("🎉 모든 글 작성이 끝났습니다! 수고하셨어요~")
            except Exception as e:
                 st.error(f"마무리 작성 실패: {e}")

elif not api_key:
    st.info("👆 먼저 API 키를 입력해주세요.")
