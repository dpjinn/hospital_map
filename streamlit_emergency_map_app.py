import streamlit as st
import pandas as pd
import folium
from folium import IFrame
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

st.title("🏥 전국 병원 지도 서비스 (Material UI Edition)")
st.caption("병원 마커를 클릭하면 상세 정보를 카드 형태로 확인할 수 있습니다.")

region = st.selectbox("📍 지역 선택", ["전체"] + sorted(df["주소"].str[:2].unique()))
search = st.text_input("🔍 병원명 또는 주소 검색")

mask = pd.Series(False, index=df.index)

if region != "전체":
    mask |= df["주소"].str.contains(region, na=False)

if search:
    mask |= df["주소"].str.contains(search, na=False) | df["이름"].str.contains(search, na=False)

filtered = df[mask] if mask.any() else df

center = [filtered["위도"].mean(), filtered["경도"].mean()]
m = folium.Map(location=center, zoom_start=12, tiles="cartodbpositron")

# -------------------------------
# Material UI 스타일 CSS
# -------------------------------
material_css = """
<style>
.mui-card {
  font-family: 'Segoe UI', sans-serif;
  background: white;
  border-radius: 12px;
  padding: 12px 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.18);
  width: 260px;
}
.mui-title {
  font-size: 16px; font-weight: 600; margin-bottom: 6px;
}
.mui-tag {
  padding: 3px 8px;
  background: #1976d2;
  color: white;
  border-radius:6px;
  font-size: 11px;
}
</style>
"""
st.markdown(material_css, unsafe_allow_html=True)

# -------------------------------
# 마커 + Material UI 팝업
# -------------------------------

markers = []
for idx, row in filtered.iterrows():
    html = f"""
    <div class="mui-card">
      <div class="mui-title">{row['이름']}</div>
      <div>📍 {row['주소']}</div>
      <div>☎ {row['전화번호']}</div>
      <br>
      <span class="mui-tag">응급실: {row['응급실']}</span>
      <br><br>
      <a href="{row['URL']}" target="_blank">🌐 홈페이지 열기</a>
    </div>
    """
    iframe = IFrame(html, width=260, height=170)
    popup = folium.Popup(iframe, max_width=300)
    markers.append([row["위도"], row["경도"], popup])

FastMarkerCluster(markers).add_to(m)

st_folium(m, width=1000, height=720)
