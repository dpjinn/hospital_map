import streamlit as st
import pandas as pd
import folium
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium

CSV_URL = "병원데이터.csv"  # 로컬 또는 URL 경로

# ------------------------
# 데이터 로딩
# ------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL)

    # '이름' 컬럼이 없으면 병원명 관련 컬럼 자동 매핑
    if "이름" not in df.columns:
        name_col = [c for c in df.columns if "병원" in c or "명" in c]
        if name_col:
            df.rename(columns={name_col[0]: "이름"}, inplace=True)
        else:
            df["이름"] = "이름 미상"

    # 결측치 처리
    df.dropna(subset=["위도", "경도"], inplace=True)
    df["주소"] = df.get("주소", pd.Series([""]))  # 주소 컬럼 없으면 빈 문자열
    df["응급실"] = df.get("응급실", pd.Series(["정보 없음"]))
    df["전화번호"] = df.get("전화번호", pd.Series(["정보 없음"]))
    df["URL"] = df.get("URL", pd.Series(["제공되지 않음"]))

    return df

df = load_data()

# ------------------------
# 앱 제목
# ------------------------
st.title("🏥 전국 병원 지도 서비스")
st.caption("지역/병원명/주소를 검색하면 해당 병원이 지도에 표시됩니다.")

# ------------------------
# 검색 UI
# ------------------------
region = st.selectbox("📍 지역 선택", ["전체"] + sorted(df["주소"].str[:2].unique()))
search_name = st.text_input("🔍 병원명 검색")
search_addr = st.text_input("📌 주소 검색")

# ------------------------
# 필터링
# ------------------------
mask = pd.Series(True, index=df.index)

if region != "전체":
    mask &= df["주소"].str.contains(region, na=False)

if search_name:
    mask &= df["이름"].str.contains(search_name, case=False, na=False)

if search_addr:
    mask &= df["주소"].str.contains(search_addr, case=False, na=False)

filtered = df[mask] if not df[mask].empty else df[df["응급실"] != "정보 없음"]
if df[mask].empty:
    st.warning("검색 결과가 없습니다. 응급실 운영 병원 목록을 표시합니다.")

# ------------------------
# 지도 생성
# ------------------------
if not filtered.empty:
    center = [filtered["위도"].mean(), filtered["경도"].mean()]
else:
    center = [36.5, 127.5]  # 기본 위치 (대한민국 중심)

m = folium.Map(location=center, zoom_start=13)

markers = []
for idx, row in filtered.iterrows():
    popup_html = f"""
    <b>{row['이름']}</b><br>
    📍 {row['주소']}<br>
    ☎ {row['전화번호']}<br>
    🚑 응급실: {row['응급실']}
    """
    markers.append([row["위도"], row["경도"], popup_html])

FastMarkerCluster(markers).add_to(m)
st_folium(m, width=1000, height=680)

# ------------------------
# 검색 결과 목록
# ------------------------
st.subheader("📋 검색 결과 목록")
for idx, row in filtered.iterrows():
    if st.button(row["이름"], key=f"btn_{idx}"):
        st.session_state["selected_hospital"] = idx

# ------------------------
# 상세 정보 모달
# ------------------------
if "selected_hospital" in st.session_state:
    row = df.loc[st.session_state["selected_hospital"]]
    with st.expander(f"🏥 {row['이름']} 상세 정보", expanded=True):
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
        if st.button("닫기"):
            st.session_state.pop("selected_hospital")
