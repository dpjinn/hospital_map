import streamlit as st
import pandas as pd
import folium
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium

CSV_URL = "병원데이터.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL)
    df.dropna(subset=["위도", "경도"], inplace=True)
    df["응급실"] = df["응급실"].fillna("정보 없음")
    return df

df = load_data()

st.title("🏥 전국 병원 지도 서비스")
st.caption("병원을 클릭하면 상세 정보를 표시합니다.")

region = st.selectbox("📍 지역 선택", ["전체"] + sorted(df["주소"].str[:2].unique()))
search = st.text_input("🔍 병원명 또는 주소 검색")

mask = pd.Series(False, index=df.index)
if region != "전체": mask |= df["주소"].str.contains(region, na=False)
if search: mask |= df["이름"].str.contains(search, na=False) | df["주소"].str.contains(search, na=False)

filtered = df[mask] if mask.any() else df

center = [filtered["위도"].mean(), filtered["경도"].mean()]
m = folium.Map(location=center, zoom_start=12, tiles="cartodbpositron")

# 마커에 팝업 대신 클릭 이벤트용 데이터만 저장
data = list(zip(filtered["위도"], filtered["경도"], filtered.index.tolist()))
FastMarkerCluster(data=data).add_to(m)

clicked = st_folium(m, height=720, width=1000)

# folium 클릭된 마커 처리
if clicked and clicked.get("last_object_clicked_tooltip"):
    idx = int(clicked["last_object_clicked_tooltip"])
    st.session_state["selected"] = idx

# 상세 모달
if "selected" in st.session_state:
    row = df.loc[st.session_state["selected"]]
    with st.modal(f"🏥 {row['이름']} 정보"):
        st.markdown(f"""
### **{row['이름']}**
📍 `{row['주소']}`  
☎ `{row['전화번호']}`  
🚑 응급실: `{row['응급실']}`  

[🌐 홈페이지 이동]({row['URL']})  
        """)
        st.button("닫기", on_click=lambda: st.session_state.pop("selected"))
