import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ====== 데이터 로드 ======
@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_csv("병원데이터.csv")  # hospital_name, address, lat, lon, subjects 등 포함
    return df

df = load_data()

st.title("응급 병원 지도 검색 시스템 🏥")

# ===== 검색 UI =====
st.subheader("🔍 병원 검색 필터")

col1, col2 = st.columns(2)

with col1:
    name_query = st.text_input("병원명으로 검색", placeholder="예: 강남세브란스")

with col2:
    address_query = st.text_input("주소로 검색", placeholder="예: 서울특별시, 부산광역시 등")

# ===== 검색 필터 적용 =====
mask = pd.Series([True] * len(df))

if name_query:
    mask &= df["병원명"].str.contains(name_query, case=False, na=False)

if address_query:
    mask &= df["주소"].str.contains(address_query, case=False, na=False)

filtered = df[mask]

st.write(f"검색 결과: {len(filtered)}개 병원")

# ===== 지도 중심점 설정 =====
if len(filtered) > 0:
    center_lat = filtered["위도"].mean()
    center_lon = filtered["경도"].mean()
else:
    center_lat, center_lon = 37.5665, 126.9780  # 서울시청 좌표 fallback

# ===== 지도 생성 =====
m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

for idx, row in filtered.iterrows():
    popup_html = f"""
    <b>{row['병원명']}</b><br>
    📍 {row['주소']}<br>
    🏥 진료과목: {row['진료과목']}<br>
    <a href='https://map.naver.com/p/search/{row['병원명']}' target='_blank'>
      네이버지도에서 보기
    </a>
    """
    folium.Marker(
        location=[row["위도"], row["경도"]],
        tooltip=row["병원명"],
        popup=folium.Popup(popup_html, max_width=280)
    ).add_to(m)

st.subheader("🗺 병원 지도")
st_folium(m, width=900, height=600)
