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
    df["주소"] = df["주소"].fillna("")
    df["응급실"] = df["응급실"].fillna("정보 없음")
    return df

df = load_data()

st.title("🏥 전국 병원 지도 서비스")
st.caption("병원을 클릭하면 상세 정보가 표시됩니다.")

region = st.selectbox("📍 지역 선택", ["전체"] + sorted(df["주소"].str[:2].unique()))
search_name = st.text_input("🔍 병원명 검색")
search_addr = st.text_input("📌 주소 검색")

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

center = [filtered["위도"].mean(), filtered["경도"].mean()]
m = folium.Map(location=center, zoom_start=12)

# ------------------------
# 1) 마커 렌더링 + 팝업 정보
# ------------------------
markers = []
for idx, row in filtered.iterrows():
    popup_html = f"""
    <b>{row['이름']}</b><br>
    📍 {row['주소']}<br>
    ☎ {row['전화번호']}<br>
    🚑 응급실: {row['응급실']}
    <br><button onclick="window.parent.postMessage({{'hospital_id': {idx}}}, '*')">상세 보기</button>
    """
    markers.append([row["위도"], row["경도"], popup_html])

FastMarkerCluster(markers).add_to(m)
map_data = st_folium(m, width=1000, height=700, returned_objects=[])

# ------------------------
# 2) 검색 리스트 제공
# ------------------------
st.subheader("📋 검색 결과")
for idx, row in filtered.iterrows():
    clicked = st.button(row["이름"])
    if clicked:
        st.session_state["selected_hospital"] = idx

# ------------------------
# 3) 상세정보 모달
# ------------------------
if "selected_hospital" in st.session_state:
    row = df.loc[st.session_state["selected_hospital"]]

    with st.modal(f"🏥 {row['이름']} 정보 상세"):
        st.markdown(f"""
### **{row['이름']}**
📍 **주소**  
`{row['주소']}`

📞 **연락처**  
`{row['전화번호']}`

🚑 **응급실 운영 여부**  
`{row['응급실']}`

🌐 **홈페이지**  
{row['URL'] if isinstance(row['URL'], str) else "제공되지 않음"}
        """)
        st.button("닫기", on_click=lambda: st.session_state.pop("selected_hospital"))
