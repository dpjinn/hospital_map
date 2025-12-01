# streamlit_emergency_map_app.py — 버전 2

import streamlit as st
import pandas as pd
import pydeck as pdk
import math

st.set_page_config(page_title="응급실/병원 지도", layout="wide", initial_sidebar_state="expanded")

# --------------------------------------------------
@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    return df

# GitHub raw URL — CSV 파일 경로
CSV_URL = "https://github.com/dpjinn/hospital_map/blob/main/%EB%B3%91%EC%9B%90%EB%8D%B0%EC%9D%B4%ED%84%B0.csv"

df = load_data(CSV_URL)

# 기본 컬럼명 매핑 (예: 위도/경도, 이름, 주소 등)
LAT_KEYS = ['위도','lat','latitude','y']
LON_KEYS = ['경도','lon','longitude','x']
NAME_KEYS = ['이름','병원명','name','의료기관명']
ADDR_KEYS = ['주소','지역','address','addr']

lat_col = next((c for c in df.columns if c in LAT_KEYS), None)
lon_col = next((c for c in df.columns if c in LON_KEYS), None)
name_col = next((c for c in df.columns if c in NAME_KEYS), None)
addr_col = next((c for c in df.columns if c in ADDR_KEYS), None)

if lat_col is None or lon_col is None or name_col is None:
    st.error("CSV에 위도/경도/이름 컬럼이 필요합니다.")
    st.stop()

df['__lat'] = pd.to_numeric(df[lat_col], errors='coerce')
df['__lon'] = pd.to_numeric(df[lon_col], errors='coerce')
df = df.dropna(subset=['__lat','__lon'])

st.title("응급실/병원 지도 서비스 (ver 2)")

# --- 지역 그룹화 매핑 예시 ---
def categorize_region(addr):
    # 실제 주소 문자열(addr)에 포함된 키워드로 그룹화
    if any(x in addr for x in ['서울','경기','인천']):
        return '수도권'
    if any(x in addr for x in ['부산','울산','경남','경북','대구']):
        return '영남권'
    if any(x in addr for x in ['대전','세종','충남','충북']):
        return '충청권'
    if any(x in addr for x in ['광주','전남','전북']):
        return '호남권'
    if any(x in addr for x in ['강원']):
        return '강원권'
    return '기타'

df['region_group'] = df[addr_col].astype(str).apply(categorize_region)

# --- 사이드바: 필터 UI ---
st.sidebar.header("🔎 필터")
keyword = st.sidebar.text_input("병원명 또는 진료과목 검색 (키워드)")

region_groups = sorted(df['region_group'].unique().tolist())
sel_regions = st.sidebar.multiselect("지역 그룹 선택", options=region_groups, default=None)

# 진료과목 필터 (CSV에 '진료과목' 또는 비슷한 컬럼이 있다면)
clinic_col = '진료과목' if '진료과목' in df.columns else None
if clinic_col:
    all_clinics = sorted(df[clinic_col].dropna().astype(str).unique().tolist())
    sel_clinics = st.sidebar.multiselect("진료과목 선택", options=all_clinics, default=None)
else:
    sel_clinics = None

# 응급실만 보기 스위치 (CSV에 '응급실' 컬럼명 등 포함 여부)
er_col = '응급실' if '응급실' in df.columns else None
show_only_er = st.sidebar.checkbox("응급실만 보기", value=False)

# --- 필터 적용 ---
working = df.copy()

if keyword:
    working = working[working[name_col].astype(str).str.contains(keyword, case=False, na=False) | 
                      (clinic_col and working[clinic_col].astype(str).str.contains(keyword, case=False, na=False))]

if sel_regions:
    working = working[working['region_group'].isin(sel_regions)]

if sel_clinics:
    working = working[working[clinic_col].isin(sel_clinics)]

if show_only_er and er_col:
    working = working[working[er_col].astype(str).str.contains('응급', case=False, na=False)]

# --- 지도에 타입별 색상 표시 ---
def color_by_type(row):
    if er_col and str(row.get(er_col, '')).lower().find('응급') >= 0:
        return [255, 0, 0]  # 빨강 — 응급실
    # 예: 진료과목에 따라 색상 다르게
    if clinic_col:
        s = str(row.get(clinic_col, '')).lower()
        if '내과' in s:
            return [0, 0, 255]  # 파랑
        if '외과' in s:
            return [0, 128, 0]  # 초록
        if '치과' in s:
            return [128, 0, 128]  # 보라
    return [0, 0, 0]  # 기본 검정

working['color'] = working.apply(color_by_type, axis=1)

# --- 지도 표시 ---
if not working.empty:
    st.subheader(f"결과 ({len(working)}곳)")

    midpoint = (working['__lat'].mean(), working['__lon'].mean())
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=working.to_dict(orient='records'),
        get_position='[__lon, __lat]',
        get_radius=200,
        get_fill_color='color',
        pickable=True,
        auto_highlight=True,
    )
    view_state = pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=7)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state,
                             tooltip={"html": "<b>{"+name_col+"}</b><br/>{주소}<br/>{__lat}, {__lon}", "style": {"color":"#000"}}))

    if st.checkbox("목록 보기"):
        st.dataframe(working[[name_col, addr_col, 'region_group', clinic_col if clinic_col else None, er_col if er_col else None, '__lat', '__lon']])
else:
    st.warning("조건에 맞는 병원이 없습니다.")

    # 응급실만 보기 혹은 키워드로도 없을 경우, 가까운 병원 3곳 안내
    user_lat = st.sidebar.number_input('내 위도', value=37.5665, format="%.6f")
    user_lon = st.sidebar.number_input('내 경도', value=126.9780, format="%.6f")

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        c = 2*math.asin(math.sqrt(a))
        return R * c

    df2 = df.copy()
    df2['__lat'] = pd.to_numeric(df2['__lat'], errors='coerce')
    df2['__lon'] = pd.to_numeric(df2['__lon'], errors='coerce')
    df2 = df2.dropna(subset=['__lat','__lon'])

    df2['dist'] = df2.apply(lambda r: haversine(user_lat, user_lon, r['__lat'], r['__lon']), axis=1)
    nearest = df2.nsmallest(3, 'dist')
    st.subheader("가장 가까운 병원/응급실 3곳 (조건 미충족 시)")
    for _, r in nearest.iterrows():
        st.markdown(f"- **{r[name_col]}** — 거리: {r['dist']:.2f} km, 주소: {r[addr_col]}")

    # 지도: 사용자 위치 + 병원
    map_df = nearest
    user_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{'__lat': user_lat, '__lon': user_lon, 'label':'내 위치'}],
        get_position='[__lon, __lat]',
        get_radius=300,
        get_fill_color=[0,0,0],
        pickable=True
    )
    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df.to_dict(orient='records'),
        get_position='[__lon, __lat]',
        get_radius=300,
        get_fill_color='color',
        pickable=True
    )
    view_state = pdk.ViewState(latitude=user_lat, longitude=user_lon, zoom=7)
    st.pydeck_chart(pdk.Deck(layers=[user_layer, hospital_layer], initial_view_state=view_state))

