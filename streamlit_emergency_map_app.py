import streamlit as st
import pandas as pd
import folium
from folium.plugins import FastMarkerCluster
import requests
from streamlit_folium import st_folium

CSV_URL = "병원데이터.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL)
    df.dropna(subset=["위도", "경도"], inplace=True)
    return df

df = load_data()

st.title("🏥 전국 병원 지도 서비스")

region = st.selectbox("📍 지역 선택", ["전체"] + sorted(df["주소"].str[:2].unique()))
search_name = st.text_input("🔍 병원명 검색")
search_addr = st.text_input("📌 주소/지역 검색")

filtered = df.copy()

# ===== OR 조건 검색 지원 =====
mask = pd.Series([False] * len(df))

if region != "전체":
    mask |= df["주소"].str.contains(region)

if search_name:
    mask |= df["이름"].str.contains(search_name)

if search_addr:
    mask |= df["주소"].str.contains(search_addr)

if mask.any():
    filtered = df[mask]

# ===== 지도 중심 자동 이동 =====
if not filtered.empty:
    center = [filtered["위도"].mean(), filtered["경도"].mean()]
else:
    st.warning("검색 결과가 없습니다. 가장 가까운 응급실을 안내합니다.")
    filtered = df[df["응급실"].notna()]
    center = [filtered["위도"].mean(), filtered["경도"].mean()]

m = folium.Map(location=center, zoom_start=12)

# ===== Fast Marker Cluster 성능 최적화 =====
coords = filtered[["위도", "경도"]].values.tolist()
names = filtered["이름"].tolist()

FastMarkerCluster(data=[(*coord, name) for coord, name in zip(coords, names)]).add_to(m)

st_folium(m, width=1000, height=700)
