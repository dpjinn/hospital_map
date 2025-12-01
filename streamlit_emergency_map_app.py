import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

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
# 검색 필터 UI
# ===============================
col1, col2, col3 = st.columns(3)
region = col1.text_input("🔎 지역 검색 (예: 강남, 광안리, 수원)").strip()
dept = col2.multiselect("🩺 진료과목 선택", sorted(df["진료과목"].unique()))
day = col3.selectbox("📅 요일 선택", ["전체", "월", "화", "수", "목", "금", "토", "일", "공휴일"])

# -------------------------------
# 진료과목 색상 자동 배정
# -------------------------------
unique_depts = df["진료과목"].unique()
palette = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
           "#911eb4", "#46f0f0", "#f032e6", "#008080", "#000075"]
color_map = {d: palette[i % len(palette)] for i, d in enumerate(unique_depts)}

# -------------------------------
# 데이터 필터링
# -------------------------------
filtered = df.copy()
if region:
    filtered = filtered[filtered["주소"].str.contains(region, case=False, na=False)]
if dept:
    filtered = filtered[filtered["진료과목"].isin(dept)]
if day != "전체":
    filtered = filtered[filtered[day] == "Y"]

st.write(f"🔍 검색된 병원 수: **{len(filtered)}개**")

# -------------------------------
# 주소 기반 사용자 중심 지도 이동
# -------------------------------
center = [37.5665, 126.9780]  # 기본: 서울 시청

if region:
    try:
        geolocator = Nominatim(user_agent="hospital_map")
        location = geolocator.geocode(region)
        if location:
            center = [location.latitude, location.longitude]
    except:
        pass

# -------------------------------
# 지도 생성 + 마커 클러스터
# -------------------------------
m = folium.Map(location=center, zoom_start=11)
cluster = MarkerCluster().add_to(m)

for _, row in filtered.iterrows():
    popup_html = (
        f"""
        <b>{row['이름']}</b><br>
        📍 {row['주소']}<br>
        📞 {row['전화번호']}<br>
        🩺 <span style="color:{color_map[row['진료과목']]}; font-weight:bold;">
        {row['진료과목']}
        </span><br>
        <button onclick="parent.postMessage({{'event':'modal','id':'{row['이름']}'}}, '*');">
            상세 정보 보기
        </button>
        """
    )
    folium.CircleMarker(
        location=[row["위도"], row["경도"]],
        radius=6,
        color=color_map[row["진료과목"]],
        fill=True, fill_color=color_map[row["진료과목"]],
        popup=folium.Popup(popup_html, max_width=300)
    ).add_to(cluster)

# 범례 박스
legend_html = """
<div style="
position: fixed; bottom: 30px; right: 30px; width: 180px;
background: white; z-index:9999; padding: 10px; border-radius: 10px;
box-shadow: 0 0 5px rgba(0,0,0,0.3); font-size: 14px;">
<b>🩺 진료과목 색상 범례</b><br>
"""
for d, c in color_map.items():
    legend_html += f'<span style="background:{c}; width:12px; height:12px; display:inline-block; margin-right:5px;"></span>{d}<br>'
legend_html += "</div>"

m.get_root().html.add_child(folium.Element(legend_html))
result = st_folium(m, width=1100, height=700)

# -------------------------------
# 병원 상세 정보 페이지 모달
# -------------------------------
if result and "last_object_clicked" in result and result["last_object_clicked"] is not None:
    name = result["last_object_clicked"]["popup"].split("<br>")[0].replace("<b>", "").replace("</b>", "")
    detail = df[df["이름"] == name].iloc[0]

    with st.modal(f"🏥 {name} 상세 정보"):
        st.subheader(name)
        st.write(f"• 📍 주소: {detail['주소']}")
        st.write(f"• 📞 전화번호: {detail['전화번호']}")
        st.write(f"• 🩺 진료과목: {detail['진료과목']}")
        st.write("• ⏱ 영업 요일:")
        st.dataframe(detail[["월", "화", "수", "목", "금", "토", "일", "공휴일"]].T)

        if detail["응급실"] == "Y":
            st.success("🚨 응급실 운영 병원입니다.")
