import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

CSV_URL = "병원데이터.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL)
    df = df.dropna(subset=["위도", "경도"])
    return df

df = load_data()

st.set_page_config(page_title="전국 병원 지도", layout="wide")
st.title("🏥 전국 병원 검색 지도")

# ===============================
# 🔍 검색 필터 UI
# ===============================

col1, col2, col3 = st.columns(3)
region = col1.text_input("🔎 지역 검색 (예: 강남, 대구 등)").strip()
dept = col2.multiselect("🩺 진료과목 선택", sorted(df["진료과목"].unique()))
day = col3.selectbox("📅 요일 선택", ["전체", "월", "화", "수", "목", "금", "토", "일", "공휴일"])

# ===============================
# 🎨 진료과목별 색상 자동 매핑
# ===============================
unique_departments = df["진료과목"].unique()
palette = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8",
    "#f58231", "#911eb4", "#46f0f0", "#f032e6", "#008080", "#000075"
]
color_map = {dept: palette[i % len(palette)] for i, dept in enumerate(unique_departments)}

# ===============================
# 📦 데이터 필터링
# ===============================
filtered = df.copy()

if region:
    filtered = filtered[filtered["주소"].str.contains(region, case=False, na=False)]

if dept:
    filtered = filtered[filtered["진료과목"].isin(dept)]

if day != "전체":
    filtered = filtered[filtered[day] == "Y"]

st.write(f"🔍 검색된 병원 수: **{len(filtered)}개**")

# ===============================
# 🗺 지도 생성 + 마커 클러스터링
# ===============================
if len(filtered) == 0:
    st.warning("검색된 병원이 없습니다. 가까운 응급실을 안내합니다.")
    emergency = df[df["응급실"] == "Y"].head(1)
    st.write("🚨 가장 가까운 응급실:")
    st.write(emergency[["이름", "주소", "전화번호"]])
else:
    center = [filtered["위도"].mean(), filtered["경도"].mean()]
    m = folium.Map(location=center, zoom_start=11)

    cluster = MarkerCluster().add_to(m)

    for _, row in filtered.iterrows():
        folium.CircleMarker(
            location=[row["위도"], row["경도"]],
            radius=6,
            color=color_map[row["진료과목"]],
            fill=True,
            fill_opacity=0.8,
            popup=f"{row['이름']}<br>{row['주소']}<br>{row['전화번호']}"
        ).add_to(cluster)

    # =======================
    # 📍 범례 HTML 오버레이 추가
    # =======================
    legend_html = """
    <div style="
        position: fixed; 
        bottom: 30px; right: 30px; width: 180px; 
        background: white; z-index:9999; 
        padding: 10px; border-radius: 10px;
        box-shadow: 0 0 5px rgba(0,0,0,0.3);
        font-size: 14px;">
        <b>🩺 진료과목 색상 범례</b><br>
    """
    for name, color in color_map.items():
        legend_html += f'<span style="background:{color}; width:12px; height:12px; display:inline-block; margin-right:5px;"></span>{name}<br>'
    legend_html += "</div>"

    m.get_root().html.add_child(folium.Element(legend_html))
    st_folium(m, width=1100, height=700)

