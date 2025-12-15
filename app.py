import streamlit as st
import google.generativeai as genai
from PIL import Image
import time

# ==========================================
# 1. 화면 기본 설정
# ==========================================
st.set_page_config(page_title="부동산 블로그 작가", page_icon="✍️")
st.title("✍️ 부동산 블로그 상세 글쓰기")
st.caption("사진만 넣으면 전문가처럼 글을 써드립니다! (오류 방지 기능 탑재 🛡️)")

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
# 3. [핵심] 오뚝이 함수 (에러나면 기다렸다가 다시 함)
# ==========================================
def generate_content_with_retry(model, prompt, image=None):
    max_retries = 3  # 최대 3번까지 재시도
    for attempt in range(max_retries):
        try:
            if image:
                return model.generate_content([prompt, image])
            else:
                return model.generate_content(prompt)
        except Exception as e:
            error_msg = str(e)
            # 429 에러(속도제한)가 뜨면
            if "429" in error_msg:
                wait_time = 20 # 20초 대기
                st.warning(f"⚠️ 구글 AI가 너무 바쁘대요! {wait_time}초만 쉬었다가 다시 할게요... (시도 {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue # 다시 시도
            else:
                # 다른 에러면 그냥 멈춤
                raise e
    raise Exception("재시도 횟수를 초과했습니다. 잠시 후 다시 시도해주세요.")

# ==========================================
# 4. 메인 기능
# ==========================================
if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # 모델 자동 선택 로직
        selected_model_name = ""
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # 1.5-flash 모델을 최우선으로 찾습니다 (속도와 안정성 위해)
            for name in available_models:
                if "gemini-1.5-flash" in name and "latest" in name:
                    selected_model_name = name
                    break
            if not selected_model_name:
                for name in available_models:
                    if "flash" in name:
                        selected_model_name = name
                        break
            if not selected_model_name and available_models:
                selected_model_name = available_models[0]

            model = genai.GenerativeModel(selected_model_name)
            
        except Exception as e:
            st.error(f"AI 모델 연결 중 오류: {e}")
            st.stop()
            
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
                # 새로 만든 오뚝이 함수 사용!
                intro_res = generate_content_with_retry(model, intro_prompt)
                st.success("✅ 도입부 작성 완료!")
                st.subheader("📝 [1] 제목 및 인사말")
                st.text_area("도입부 복사하기", value=intro_res.text, height=200)
            except Exception as e:
                st.error(f"글쓰기 실패. 잠시 후 다시 시도해주세요. ({e})")

        st.divider()

        # 2️⃣ 사진별 본문 작성 (반복문)
        st.subheader("📝 [2] 사진별 상세 설명")
        st.info("👇 사진 순서대로 글이 생성됩니다. 사진 밑에 글을 복사해서 쓰세요!")

        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            # 안내 메시지
            status_text = st.empty()
            status_text.text(f"📸 {i+1}번째 사진 분석 중...")

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
                
                # 새로 만든 오뚝이 함수 사용! (실패하면 20초 쉼)
                response = generate_content_with_retry(model, img_prompt, image)
                
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.image(image, use_container_width=True)
                with c2:
                    st.text_area(f"{i+1}번째 사진 설명", value=response.text, height=150)
                
                status_text.text(f"✅ {i+1}번째 사진 완료!")
                
            except Exception as e:
                st.error(f"{i+1}번째 사진 처리 실패: {e}")

            # 진행률 업데이트
            progress_bar.progress((i + 1) / len(uploaded_files))
            
            # 구글 무료 버전을 위해 강제로 5초씩 쉬어줍니다. (안전빵)
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
                # 오뚝이 함수 사용
                outro_res = generate_content_with_retry(model, outro_prompt)
                
                st.subheader("📝 [3] 마무리 및 해시태그")
                st.text_area("마무리 복사하기", value=outro_res.text, height=200)
                st.success("🎉 모든 글 작성이 끝났습니다! 수고하셨어요~")
            except Exception as e:
                 st.error(f"마무리 작성 실패: {e}")

elif not api_key:
    st.info("👆 먼저 API 키를 입력해주세요.")