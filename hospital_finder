import streamlit as st
import pandas as pd
from streamlit_folium import folium_static
import folium
import numpy as np

# --- 1. 기본 설정 및 데이터 로드 ---
st.set_page_config(
    page_title="🏥 병원 찾기 서비스",
    layout="wide",  # 전체 폭 사용
    initial_sidebar_state="expanded"
)

# 데이터 로드 및 캐싱 (성능 최적화)
@st.cache_data
def load_data(file_path):
    data = pd.read_csv(file_path)
    # 위도(위도)와 경도(경도)가 유효한 행만 필터링하고 숫자로 변환
    data = data.dropna(subset=['위도', '경도'])
    data['위도'] = pd.to_numeric(data['위도'], errors='coerce')
    data['경도'] = pd.to_numeric(data['경도'], errors='coerce')
    data = data.dropna(subset=['위도', '경도'])
    return data

DATA_FILE = '병원데이터.csv'
try:
    df = load_data(DATA_FILE)
except FileNotFoundError:
    st.error(f"⚠️ **{DATA_FILE}** 파일을 찾을 수 없습니다. 파일 이름을 확인해주세요.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ 데이터 로드 중 오류가 발생했습니다: {e}")
    st.stop()


# --- 2. 사이드바 (검색 필터) ---
st.sidebar.header("🔍 병원 검색 필터")

# 1) 응급실 운영 여부
# '응급실' 컬럼이 1인 경우 응급실 운영으로 간주 (데이터 구조 분석 결과)
emergency_options = {
    "전체": "all",
    "✅ 응급실 운영": 1,
    "❌ 응급실 미운영": 0
}
selected_emergency = st.sidebar.radio(
    "응급실 운영 여부",
    list(emergency_options.keys()),
    index=0
)

# 2) 요일 선택 및 운영 시간
day_columns = ['월', '화', '수', '목', '금', '토', '일', '공휴일']
selected_day = st.sidebar.selectbox("운영 요일", ["--- 선택 ---"] + day_columns)

current_time = pd.Timestamp.now().strftime("%H:%M")

# 3) 검색 키워드 (병원 이름, 주소(지역), 진료과목)
search_query = st.sidebar.text_input(
    "키워드 검색 (병원명, 지역, 진료과목)",
    placeholder="예: 삼성, 강남, 내과"
)

# --- 3. 데이터 필터링 ---
filtered_df = df.copy()

# 1) 응급실 필터링
emergency_value = emergency_options[selected_emergency]
if emergency_value == 1:
    filtered_df = filtered_df[filtered_df['응급실'] == 1]
elif emergency_value == 0:
    # 응급실 컬럼이 1이 아닌 모든 경우를 미운영으로 간주
    filtered_df = filtered_df[filtered_df['응급실'] != 1] 

# 2) 요일/시간 필터링
if selected_day != "--- 선택 ---":
    # 운영 시간 데이터가 있는 행만 필터링
    filtered_df = filtered_df.dropna(subset=[selected_day])
    
    # 현재 시각을 기준으로 운영 중인 병원 필터링 (간단 구현)
    # 실제로는 시간 문자열 파싱 로직이 필요하지만, 여기서는 데이터가 있는 병원만 표시
    # 필터링 로직을 넣으려면 데이터 형식에 따라 복잡해지므로, 일단은 해당 요일 운영 병원만 표시
    st.sidebar.info(f"선택: **{selected_day}** 운영 병원")


# 3) 키워드 검색 필터링
if search_query:
    search_query = search_query.lower()
    # 이름, 주소, 진료과목 컬럼에 키워드가 포함된 경우 필터링
    filtered_df = filtered_df[
        filtered_df.apply(lambda row: 
            search_query in str(row['이름']).lower() or
            search_query in str(row['주소']).lower() or
            search_query in str(row['진료과목']).lower(), 
            axis=1
        )
    ]

# --- 4. 메인 콘텐츠 (지도 및 결과 표시) ---
st.title("🏥 대한민국 병원 찾기 지도 서비스")
st.markdown(f"#### 현재 검색 조건에 맞는 병원: **{len(filtered_df)}**개")

col1, col2 = st.columns([7, 3])

with col1:
    st.subheader("📍 병원 위치 지도")
    
    if len(filtered_df) == 0:
        st.warning("선택하신 조건에 맞는 병원이 없습니다. 필터를 조정해주세요.")
    else:
        # Folium 지도 초기화
        # 첫 번째 필터링된 병원의 위치를 지도의 중심으로 설정
        initial_lat = filtered_df['위도'].iloc[0]
        initial_lon = filtered_df['경도'].iloc[0]
        
        m = folium.Map(
            location=[initial_lat, initial_lon],
            zoom_start=11,  # 초기 줌 레벨 설정
            control_scale=True # 지도 과부하 방지를 위한 컨트롤
        )

        # 지도에 마커 추가
        for idx, row in filtered_df.iterrows():
            # 팝업에 표시될 HTML 내용 생성
            popup_html = f"""
            <h4>**{row['이름']}**</h4>
            <p>전화: {row['전화번호'] if pd.notna(row['전화번호']) else '-'}</p>
            <p>주소: {row['주소'] if pd.notna(row['주소']) else '-'}</p>
            <p>응급실: {'✅ 운영 중' if row['응급실'] == 1 else '❌ 미운영'}</p>
            <a href="{row['URL']}" target="_blank">홈페이지 바로가기</a>
            """
            
            # 응급실 유무에 따른 마커 색상 설정
            marker_color = 'red' if row['응급실'] == 1 else 'blue'
            
            # Folium 마커 추가 (팝업 포함)
            folium.Marker(
                location=[row['위도'], row['경도']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=row['이름'],
                icon=folium.Icon(color=marker_color, icon='hospital')
            ).add_to(m)

        # 지도 크기 조절 (과부하 방지 및 UI 깔끔함 유지)
        folium_static(m, width=900, height=550)
        
with col2:
    st.subheader("💡 상세 정보")
    
    if len(filtered_df) > 0:
        st.info("지도상의 마커를 클릭하거나, 아래 표에서 병원을 선택하여 상세 정보를 확인하세요.")
        
        # 상세 정보 표시를 위한 데이터프레임
        display_cols = ['이름', '전화번호', '주소', '진료과목', '응급실', '월', '화', '수', '목', '금', '토', '일', '공휴일']
        display_df = filtered_df.reindex(columns=display_cols, fill_value='-')
        display_df['응급실'] = display_df['응급실'].apply(lambda x: '✅ 운영 중' if x == 1 else '❌ 미운영')
        
        # 사용자 선택을 위한 라디오 버튼
        selected_hospital_name = st.radio(
            "상세 정보 조회",
            display_df['이름'].tolist(),
            index=0,
            key='hospital_radio'
        )
        
        if selected_hospital_name:
            selected_hospital = filtered_df[filtered_df['이름'] == selected_hospital_name].iloc[0]
            
            st.markdown("---")
            st.markdown(f"### {selected_hospital['이름']}")
            
            st.write(f"**📞 전화번호:** {selected_hospital['전화번호'] if pd.notna(selected_hospital['전화번호']) else '-'}")
            st.write(f"**🏠 주소:** {selected_hospital['주소'] if pd.notna(selected_hospital['주소']) else '-'}")
            st.write(f"**🩺 진료과목:** {selected_hospital['진료과목'] if pd.notna(selected_hospital['진료과목']) else '-'}")
            st.write(f"**🚨 응급실 운영:** {'✅ 운영 중' if selected_hospital['응급실'] == 1 else '❌ 미운영'}")
            
            if pd.notna(selected_hospital['URL']) and selected_hospital['URL'] != '':
                st.markdown(f"**🔗 웹사이트:** [바로가기]({selected_hospital['URL']})")
                
            st.markdown("##### 🕒 요일별 운영 시간")
            time_data = {
                '요일': day_columns,
                '운영 시간': [selected_hospital[day] if pd.notna(selected_hospital[day]) else '휴진 / 정보 없음' for day in day_columns]
            }
            time_df = pd.DataFrame(time_data)
            st.table(time_df)
    
# --- 5. 데이터 테이블 표시 (선택 사항) ---
st.markdown("---")
st.markdown("#### 엑셀 형식 데이터 테이블 (검색 결과)")
st.dataframe(filtered_df[['이름', '전화번호', '주소', '응급실', '월', '화', '수', '목', '금', '토', '일', '공휴일']], use_container_width=True)
