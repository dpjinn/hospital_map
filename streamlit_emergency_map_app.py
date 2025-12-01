import streamlit as st
import pandas as pd
import folium
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium

CSV_URL = "병원데이터.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL)

    # 컬럼명 보호 처리
    # '이름' 컬럼이 없으면 병원명 관련 컬럼 자동 매핑
    if "이름" not in df.columns:
        name_col = [c for c in df.columns if "병원" in c or "명" in c]
        if name_col:
            df.rename(columns={name_col[0]: "이름"}, inplace=True)
        else:
            df["이름"] = "이름 미상"

    # 결측치 처리
    df.dropna(subset=["위도", "경도"], inplace=True)
    df["주소"] = df["주소"].fillna("")
    df["응급실"] = df["응급실"].fillna("정보 없음")
    df["전화번호"] = df.get("전화번호", "").fillna("정보 없음")
    df["URL"] = df.get("URL", "").fillna("제공되지 않음")

    return df


df = load_data()

st.title("🏥 전국 병원 지도 서비스")
st.caption("지역/병원명/주소를 검색하면 해당 병원이 지도에 표시됩니다.")

# ------------------------
# 🔍 검색 UI 구성
# ------------------------
region = st.selectbox("📍 지역 선택", ["전체"] + sorted(df["주소"].str[:2].unique()))
search_name = st.text_input("🔍 병원명 검색")
search_addr = st.text_input("📌 주소 검색")

# ------------------------
# 🔎 필터링 마스크 생성 (조건 하나만 있어도 검색되도록)
# ------------------------
mask = pd.Series(True, index=df.index)

if region != "전체":
    mask &= df["주소"].str.contains(region, na=False)

if search_name:
    mask &= df["이름"].str.contains(search_name, case=False, na=False)

if search_addr:
    mask &= df["주소"].str.contains(search_addr, case=False, na=False)

# 필터 후 데이터 결정
if df[mask].empty:
    st.warning("검색 결과가 없습니다. 응급실 운영 병원 목록을 표시합니다.")
    filtered = df[df["응급실"] != "정보 없음"]
else:
    filtered = df[mask]

# ------------------------
# 🗺 지도 생성 및 마커 표시
# ------------------------
center = [filtered["위도"].mean(), filtered["경도"].mean()]
m = folium.Map(location=center, zoom_start=13)

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

map_data = st_folium(m, width=1000, height=680, returned_objects=[])

# ------------------------
# 📋 검색 결과 리스트
# ------------------------
st.subheader("📋 검색 결과 목록")
for idx, row in filtered.iterrows():
    if st.button(row["이름"], key=f"btn_{idx}"):
        st.session_state["selected_hospital"] = idx

# ------------------------
# 🪟 상세 정보 모달
# ------------------------
if "selected_hospital" in st.session_state:
    row = df.loc[st.session_state["selected_hospital"]]
    with st.modal(f"🏥 {row['이름']} 상세 정보"):
        st.markdown(f"""
### **{row['이름']}**

📍 **주소**  
`{row['주소']}`

📞 **연락처**  
`{row['전화번호']}`

🚑 **응급실 운영 여부**  
`{row['응급실']}`

🌐 **홈페이지**  
{row['URL']}
        """)
        st.button("닫기", on_click=lambda: st.session_state.pop("selected_hospital"))
