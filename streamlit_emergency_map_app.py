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
# 검색 UI
# ===============================
col1, col2, col3 = st.columns(3)

region = col1.text_input("🔍 지역 검색 (예: 강남, 광안리, 대구)").strip()
day = col2.selectbox("📅 요일 선택", ["전체", "월", "화", "수", "목", "금", "토", "일", "공휴일"])
emergency_only = col3.checkbox("🚨 응급실 운영 병원만 보기", value=False)

# ===============================
# 검색 로직 (하나라도 입력되면 필터)
# ===============================
filtered = df.copy()

if region:
    filtered = filtered[filtered["주소"].str.contains(region, case=False, na=False)]

if day != "전체":
    filtered = filtered[filtered[day] == "Y"]

if emergency_only:
    filtered = filtered[filtered["응급실"] == "Y"]

st.write(f"🔎 검색된 병원 수: **{len(filtered)}개**")

# ===============================
# 지도 영역 최적화 / 렉 방지
# ===============================
if len(filtered) > 0:
    # 지도는 검색된 병원 범위만 표시 → 렉 감소
    bounds = [
        [filtered["위도"].min(), filtered["경도"].min()],
        [filtered["위도"].max(), filtered["경도"].max()],
    ]
    m = folium.Map()
    m.fit_bounds(bounds)

    cluster = MarkerCluster().add_to(m)

    for _, row in filtered.iterrows():
        popup_html = f"""
        <b>{row['이름']}</b><br>
        📍 {row['주소']}<br>
        📞 {row['전화번호']}<br>
        <button onclick="parent.postMessage({{'event':'modal','id':'{row['이름']}'}}, '*');">
            상세 정보 보기
        </button>
        """
        folium.CircleMarker(
            location=[row["위도"], row["경도"]],
            radius=6,
            color="#2b78e4",
            fill=True,
            fill_color="#2b78e4",
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(cluster)

    result = st_folium(m, width=1100, height=700)

else:
    st.warning("조건에 맞는 병원을 찾지 못했습니다. 가까운 응급실을 안내합니다.")
    emergency = df[df["응급실"] == "Y"].head(1)
    st.write(emergency[["이름", "주소", "전화번호"]])

# ===============================
# 병원 상세 정보 모달
# ===============================
if "last_object_clicked" in result and result["last_object_clicked"]:
    name = result["last_object_clicked"]["popup"].split("<br>")[0].replace("<b>", "").replace("</b>", "")
    detail = df[df["이름"] == name].iloc[0]

    with st.modal(f"🏥 {name} 상세 정보"):
        st.subheader(name)
        st.write(f"• 📍 주소: {detail['주소']}")
        st.write(f"• 📞 전화번호: {detail['전화번호']}")
        st.write("• ⏱ 영업 요일:")
        st.dataframe(detail[["월", "화", "수", "목", "금", "토", "일", "공휴일"]].T)

        if detail["응급실"] == "Y":
            st.success("🚨 응급실 운영 병원입니다.")
