import streamlit as st
import pandas as pd
from streamlit_folium import folium_static
import folium
from folium.plugins import MarkerCluster # <--- 🌟 마커 클러스터링을 위한 임포트
import numpy as np

# --- 1. 기본 설정 및 데이터 로드 (캐싱 적용) ---
st.set_page_config(
    page_title="🏥 병원 찾기 서비스 (최적화)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# st.cache_data: 데이터가 변경되지 않는 한 파일을 다시 읽거나 전처리하지 않음
@st.cache_data
def load_and_preprocess_data(file_path):
    """데이터를 로드하고 지도 표시를 위해 전처리합니다."""
    data = pd.read_csv(file_path)
    
    # 1. 필수 컬럼 확인 및 클리닝
    data = data.rename(columns={'위도': 'lat', '경도': 'lon', '이름': 'name'})
    
    # 위도, 경도 유효성 검사 및 숫자로 변환
    data = data.dropna(subset=['lat', 'lon'])
    data['lat'] = pd.to_numeric(data['lat'], errors='coerce')
    data['lon'] = pd.to_numeric(data['lon'], errors='coerce')
    data = data.dropna(subset=['lat', 'lon'])
    
    # 응급실 컬럼을 숫자로 통일 (NaN/다른 값은 0으로 간주)
    data['응급실'] = data['응급실'].fillna(0).astype(int).apply(lambda x: 1 if x >= 1 else 0)
    
    # 검색 속도 향상을 위해 검색 대상 컬럼을 하나의 문자열로 결합 (전처리)
    data['searchable_text'] = (
        data['name'].astype(str).str.lower() + " " +
        data['주소'].astype(str).str.lower() + " " +
        data['진료과목'].astype(str).str.lower()
    )
    
    return data

DATA_FILE = 'hospital_data.csv'
try:
    df_raw = load_and_preprocess_data(DATA_FILE)
except FileNotFoundError:
    st.error(f"⚠️ **{DATA_FILE}** 파일을 찾을 수 없습니다. 파일 이름을 확인해주세요.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ 데이터 로드 중 오류가 발생했습니다: {e}")
    st.stop()

# --- 2. 사이드바 (검색 필터) ---
st.sidebar.header("🔍 병원 검색 필터")

# 1) 응급실 운영 여부
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

# 3) 검색 키워드 (병원 이름, 주소(지역), 진료과목)
search_query = st.sidebar.text_input(
    "키워드 검색 (병원명, 지역, 진료과목)",
    placeholder="예: 삼성, 강남, 내과"
).strip().lower() # <--- 입력과 동시에 소문자 변환

# --- 3. 데이터 필터링 (최적화된 벡터화 연산) ---
filtered_df = df_raw.copy()

# 1) 응급실 필터링
emergency_value = emergency_options[selected_emergency]
if emergency_value != "all":
    filtered_df = filtered_df[filtered_df['응급실'] == emergency_value]

# 2) 요일/시간 필터링
if selected_day != "--- 선택 ---":
    # 해당 요일 운영 시간이 NaN이 아닌 행만 필터링
    filtered_df = filtered_df[filtered_df[selected_day].notna()]
    st.sidebar.info(f"필터: **{selected_day}** 운영 데이터가 있는 병원")

# 3) 키워드 검색 필터링 (🌟 Vectorization 적용)
if search_query:
    # 미리 결합된 searchable_text 컬럼에 키워드가 포함된 행만 선택
    filtered_df = filtered_df[
        filtered_df['searchable_text'].str.contains(search_query, na=False)
    ]
    
# --- 4. 메인 콘텐츠 (지도 및 결과 표시) ---
st.title("🏥 대한민국 병원 찾기 지도 서비스 (최적화 버전)")
st.markdown(f"#### 현재 검색 조건에 맞는 병원: **{len(filtered_df)}**개")

col1, col2 = st.columns([7, 3])

with col1:
    st.subheader("📍 병원 위치 지도 (마커 클러스터링 적용)")
    
    if len(filtered_df) == 0:
        st.warning("선택하신 조건에 맞는 병원이 없습니다. 필터를 조정해주세요.")
    else:
        # 지도의 중심점 계산 (필터링된 병원들의 평균 위치)
        center_lat = filtered_df['lat'].mean()
        center_lon = filtered_df['lon'].mean()
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11,
            control_scale=True # 필수: 성능 관리 기능
        )

        # 🌟 MarkerCluster 객체 생성 (성능 최적화 핵심)
        marker_cluster = MarkerCluster().add_to(m)

        # 지도에 마커 추가
        for idx, row in filtered_df.iterrows():
            # 팝업에 표시될 HTML 내용 생성
            popup_html = f"""
            <h4>**{row['name']}**</h4>
            <p>전화: {row['전화번호'] if pd.notna(row['전화번호']) else '-'}</p>
            <p>주소: {row['주소'] if pd.notna(row['주소']) else '-'}</p>
            <p>응급실: {'✅ 운영 중' if row['응급실'] == 1 else '❌ 미운영'}</p>
            <a href="{row['URL']}" target="_blank">홈페이지 바로가기</a>
            """
            
            # 응급실 유무에 따른 마커 색상 설정
            marker_color = 'red' if row['응급실'] == 1 else 'blue'
            
            # MarkerCluster에 마커 추가
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=row['name'],
                icon=folium.Icon(color=marker_color, icon='hospital')
            ).add_to(marker_cluster) # 🌟 Cluster에 추가

        # 지도 크기 조절
        folium_static(m, width=900, height=550)
        
with col2:
    st.subheader("💡 상세 정보")
    
    if len(filtered_df) > 0:
        st.info("지도상의 마커를 클릭하거나, 아래 표에서 병원을 선택하여 상세 정보를 확인하세요.")
        
        # 상세 정보 표시를 위한 데이터프레임
        display_cols = ['name', '전화번호', '주소', '진료과목', '응급실'] + day_columns
        
        # 이름 컬럼만 별도로 처리하여 라디오 버튼에 사용
        hospital_names = filtered_df['name'].tolist()
        
        # 라디오 버튼에 표시할 항목이 너무 많으면 상위 N개만 표시하도록 변경 가능
        max_display = 200 # 최대 200개까지만 표시 (렉 방지)
        
        if len(hospital_names) > max_display:
            st.warning(f"검색 결과가 {len(hospital_names)}개로 많습니다. 성능을 위해 상위 {max_display}개만 목록에 표시합니다.")
            hospital_names = hospital_names[:max_display]

        selected_hospital_name = st.radio(
            "상세 정보 조회 (목록)",
            hospital_names,
            index=0,
            key='hospital_radio'
        )
        
        if selected_hospital_name:
            selected_hospital = filtered_df[filtered_df['name'] == selected_hospital_name].iloc[0]
            
            st.markdown("---")
            st.markdown(f"### {selected_hospital['name']}")
            
            # 상세 정보 깔끔하게 표시
            st.write(f"**📞 전화번호:** {selected_hospital['전화번호'] if pd.notna(selected_hospital['전화번호']) else '-'}")
            st.write(f"**🏠 주소:** {selected_hospital['주소'] if pd.notna(selected_hospital['주소']) else '-'}")
            st.write(f"**🩺 진료과목:** {selected_hospital['진료과목'] if pd.notna(selected_hospital['진료과목']) else '-'}")
            st.write(f"**🚨 응급실 운영:** {'✅ 운영 중' if selected_hospital['응급실'] == 1 else '❌ 미운영'}")
            
            if pd.notna(selected_hospital.get('URL')) and selected_hospital.get('URL') != '':
                st.markdown(f"**🔗 웹사이트:** [바로가기]({selected_hospital['URL']})")
                
            st.markdown("##### 🕒 요일별 운영 시간")
            time_data = {
                '요일': day_columns,
                '운영 시간': [selected_hospital[day] if pd.notna(selected_hospital[day]) else '휴진 / 정보 없음' for day in day_columns]
            }
            time_df = pd.DataFrame(time_data)
            st.table(time_df)
    
# --- 5. 데이터 테이블 표시 ---
st.markdown("---")
st.markdown("#### 검색 결과 데이터 테이블")
# 불필요한 전체 컬럼 대신 필요한 정보만 표시하여 렌더링 부하 감소
table_cols = ['name', '전화번호', '주소', '진료과목', '응급실'] + day_columns
display_table_df = filtered_df.reindex(columns=table_cols).copy()
display_table_df['응급실'] = display_table_df['응급실'].apply(lambda x: '✅ 운영 중' if x == 1 else '❌ 미운영')
display_table_df = display_table_df.rename(columns={'name': '이름'})

st.dataframe(display_table_df, use_container_width=True)
