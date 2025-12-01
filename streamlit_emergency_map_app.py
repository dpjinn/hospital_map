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
mask = pd.Series(False, index=df.index)

if region != "전체":
    mask |= df["주소"].str.contains(region, na=False)

if search_name:
    mask |= df["이름"].str.contains(search_name, na=False)

if search_addr:
    mask |= df["주소"].str.contains(search_addr, na=False)

if mask.any():
    filtered = df[mask]
else:
    st.warning("검색 결과가 없습니다. 가장 가까운 응급실을 표시합니다.")
    filtered = df[df["응급실"] != "정보 없음"]


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
<b>{row['name']}</b><br>
📍 {row['address']}<br>
🏥 진료과목: {row['subjects']}<br>
"""
folium.Marker(
    location=[row["lat"], row["lng"]],
    tooltip=row["name"],
    popup=folium.Popup(popup_html, max_width=280)
).add_to(m)


st.subheader("🗺 병원 지도")
st_folium(m, width=900, height=600)
