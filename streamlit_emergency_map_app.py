# streamlit_emergency_map_app.py
# 한국어 Streamlit 앱 — 병원/응급실 지도 (색상 맵핑, 지역 그룹, 강화 검색, 장소 검색)
# 필요: streamlit, pandas, pydeck, numpy, geopy

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import math
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from functools import lru_cache

st.set_page_config(page_title="응급실/병원 지도 (컬러/검색 강화)", layout="wide")

# -------------------- 설정: GitHub raw CSV URL --------------------
CSV_URL = "병원데이터.csv"

# -------------------- 유틸: 컬럼 자동 감지 --------------------
def detect_columns(df):
    cols = {c: c for c in df.columns}
    lower = {c.lower(): c for c in df.columns}
    def find_one(candidates):
        for cand in candidates:
            if cand.lower() in lower:
                return lower[cand.lower()]
        # substring fallback
        for cname in df.columns:
            for cand in candidates:
                if cand.lower() in cname.lower():
                    return cname
        return None

    lat = find_one(['위도','lat','latitude','y'])
    lon = find_one(['경도','lon','longitude','x'])
    name = find_one(['이름','병원명','의료기관명','name'])
    addr = find_one(['주소','address','addr','지역'])
    clinic = find_one(['진료과목','과목','department','clinic'])
    er = find_one(['응급실','응급','emergency','ER'])
    return {'lat': lat, 'lon': lon, 'name': name, 'addr': addr, 'clinic': clinic, 'er': er}

# -------------------- 로드 데이터 --------------------
@st.cache_data(show_spinner=False)
def load_df(csv_url):
    df = pd.read_csv(csv_url)
    return df

try:
    df = load_df(CSV_URL)
except Exception as e:
    st.error("CSV를 로드할 수 없습니다. raw GitHub URL 및 파일명을 확인하세요.\n" + str(e))
    st.stop()

cols = detect_columns(df)

if not (cols['lat'] and cols['lon'] and cols['name']):
    st.error("CSV에 위도/경도/이름 컬럼이 필요합니다. 컬럼명이 다르면 확인해주세요.")
    st.write("감지된 컬럼:", df.columns.tolist())
    st.stop()

# 위도/경도 정리
df['__lat'] = pd.to_numeric(df[cols['lat']], errors='coerce')
df['__lon'] = pd.to_numeric(df[cols['lon']], errors='coerce')
df = df.dropna(subset=['__lat','__lon']).reset_index(drop=True)

# -------------------- 지역 그룹화 매핑 --------------------
def categorize_region(addr):
    a = str(addr)
    if any(x in a for x in ['서울','경기','인천']):
        return '수도권'
    if any(x in a for x in ['부산','울산','대구','경남','경북']):
        return '영남권'
    if any(x in a for x in ['광주','전남','전북']):
        return '호남권'
    if any(x in a for x in ['대전','세종','충남','충북']):
        return '충청권'
    if any(x in a for x in ['강원']):
        return '강원권'
    if any(x in a for x in ['제주']):
        return '제주권'
    return '기타'

addr_col = cols['addr']
if addr_col:
    df['region_group'] = df[addr_col].astype(str).apply(categorize_region)
else:
    df['region_group'] = '미상'

# -------------------- 진료과목/응급실 컬러 맵핑 --------------------
# 세분화 매핑(키워드 -> RGB)
SPECIALTY_COLOR_MAP = {
    '응급': [255, 0, 0],
    '응급실': [255,0,0],
    '내과': [0, 122, 255],
    '가정의학과': [0, 122, 255],
    '소아청소년과': [0, 200, 200],
    '외과': [0, 200, 0],
    '정형외과': [34,139,34],
    '신경외과': [60,179,113],
    '산부인과': [255,105,180],
    '치과': [128,0,128],
    '안과': [75,0,130],
    '피부과': [199,21,133],
    '정신과': [128,128,0],
    '재활의학과': [46,139,87],
    '한방': [210,105,30],
    '기타': [100,100,100],
}

clinic_col = cols['clinic']
er_col = cols['er']

def get_color_for_row(row):
    # 우선 응급실 우선 처리
    if er_col and str(row.get(er_col,'')).lower().find('응급') >= 0:
        return SPECIALTY_COLOR_MAP['응급실']
    # 진료과목 기반 추출 (복수 항목일 수 있음)
    if clinic_col:
        s = str(row.get(clinic_col,''))
        for k,v in SPECIALTY_COLOR_MAP.items():
            if k == '응급' or k == '응급실' or k == '기타':
                continue
            if k in s:
                return v
    # 주소/이름 등에서 힌트(간단)
    name = str(row.get(cols['name'],''))
    for k,v in SPECIALTY_COLOR_MAP.items():
        if k in name:
            return v
    return SPECIALTY_COLOR_MAP['기타']

df['color'] = df.apply(get_color_for_row, axis=1)

# -------------------- 사이드바: 고급 검색 UI --------------------
st.title("응급실/병원 지도 — 컬러 + 강화 검색 + 장소검색")

st.sidebar.header("검색 & 필터")

# 검색 키워드 (다중, 공백/콤마로 구분)
keyword_text = st.sidebar.text_input("키워드 (병원명 또는 진료과목) — 여러개는 공백 또는 쉼표로 구분")
keywords = [k.strip() for k in keyword_text.replace(',', ' ').split() if k.strip()]

and_or = st.sidebar.radio("키워드 매칭 방식", options=['AND', 'OR'], index=1,
                          help="AND: 모든 키워드가 포함되어야 함 / OR: 어떤 키워드든 포함되면 결과")

# 지역 그룹 선택
region_options = sorted(df['region_group'].unique().tolist())
sel_regions = st.sidebar.multiselect("지역 그룹", options=region_options, default=None)

# 진료과목 선택 (있는 경우)
clinic_options = []
if clinic_col:
    clinic_options = sorted(df[clinic_col].dropna().astype(str).unique().tolist())
sel_clinics = st.sidebar.multiselect("진료과목 필터 (직접 선택)", options=clinic_options, default=None)

# 응급실 전용
show_only_er = st.sidebar.checkbox("응급실만 보기", value=False)

# 장소 검색 (자동 중심 이동)
st.sidebar.markdown("---")
place_query = st.sidebar.text_input("장소 검색 (예: 강남역, 서울역 등)")
geocode_button = st.sidebar.button("장소로 이동")

# 사용자 위치(거리기준)
user_lat = st.sidebar.number_input("내 위도 (거리 기준)", value=37.5665, format="%.6f")
user_lon = st.sidebar.number_input("내 경도 (거리 기준)", value=126.9780, format="%.6f")

# -------------------- 고급 필터 적용 --------------------
working = df.copy()

# 키워드 필터 (병원명/진료과목 컬럼을 중심으로)
if keywords:
    def row_matches_kw(r):
        targets = []
        targets.append(str(r.get(cols['name'], '')))
        if clinic_col:
            targets.append(str(r.get(clinic_col, '')))
        joined = ' '.join(targets).lower()
        if and_or == 'AND':
            return all(k.lower() in joined for k in keywords)
        else:
            return any(k.lower() in joined for k in keywords)
    working = working[working.apply(row_matches_kw, axis=1)]

# 지역 그룹 필터
if sel_regions:
    working = working[working['region_group'].isin(sel_regions)]

# 진료과목 선택 필터
if sel_clinics:
    working = working[working[clinic_col].isin(sel_clinics)]

# 응급실
if show_only_er and er_col:
    working = working[working[er_col].astype(str).str.contains('응급', case=False, na=False)]

# -------------------- 장소 검색(geocode) --------------------
@lru_cache(maxsize=128)
def geocode_place(query):
    if not query:
        return None
    try:
        geolocator = Nominatim(user_agent="hospital_map_app")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        loc = geocode(query)
        if loc:
            return (loc.latitude, loc.longitude)
    except Exception:
        return None
    return None

place_center = None
if geocode_button and place_query:
    res = geocode_place(place_query)
    if res:
        place_center = res
    else:
        st.sidebar.warning("장소를 찾을 수 없습니다. 다른 검색어로 시도하세요.")

# -------------------- 지도 표시 --------------------
st.markdown("## 결과 지도")
if not working.empty:
    st.markdown(f"### 필터 결과: {len(working)}곳")
    midpoint_lat = working['__lat'].mean()
    midpoint_lon = working['__lon'].mean()
    # view center: 장소 검색 우선, 아니면 결과 평균
    center_lat = place_center[0] if place_center else midpoint_lat
    center_lon = place_center[1] if place_center else midpoint_lon

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=working.to_dict(orient='records'),
        get_position='[__lon, __lat]',
        get_radius=200,
        get_fill_color='color',
        pickable=True,
        auto_highlight=True,
    )
    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=11 if place_center else 7)
    tooltip_html = "<b>{" + cols['name'] + "}</b><br/>지역: {" + (addr_col if addr_col else 'region_group') + "}<br/>{__lat}, {__lon}"
    deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"html": tooltip_html, "style": {"color":"#000"}})
    st.pydeck_chart(deck, use_container_width=True)

    # 목록 보기
    if st.checkbox("목록 보기 (테이블)"):
        show_cols = [c for c in [cols['name'], addr_col, clinic_col, er_col, 'region_group', '__lat', '__lon'] if c]
        st.dataframe(working[show_cols].rename(columns=lambda x: x))
else:
    st.warning("조건에 맞는 병원이 없습니다.")
    # 가장 가까운 3곳 안내
    def haversine(lat1,lon1,lat2,lon2):
        R = 6371.0
        lat1,lon1,lat2,lon2 = map(math.radians, [lat1,lon1,lat2,lon2])
        dlat = lat2-lat1; dlon = lon2-lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        c = 2*math.asin(math.sqrt(a))
        return R * c
    temp = df.copy()
    temp['dist_km'] = temp.apply(lambda r: haversine(user_lat, user_lon, r['__lat'], r['__lon']), axis=1)
    nearest = temp.nsmallest(3, 'dist_km')
    st.subheader("가장 가까운 병원/응급실 (3곳)")
    for _, r in nearest.iterrows():
        st.markdown(f"- **{r[cols['name']]}** — {r['dist_km']:.2f} km — { (r.get(addr_col) if addr_col else '') }")
    # 지도: 내위치 + nearest
    map_df = nearest
    user_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{'__lat': user_lat, '__lon': user_lon, 'name':'내 위치'}],
        get_position='[__lon, __lat]',
        get_radius=300,
        get_fill_color=[0,0,0],
        pickable=True
    )
    hosp_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df.to_dict(orient='records'),
        get_position='[__lon, __lat]',
        get_radius=300,
        get_fill_color='color',
        pickable=True
    )
    view_state = pdk.ViewState(latitude=(user_lat+map_df['__lat'].mean())/2,
                               longitude=(user_lon+map_df['__lon'].mean())/2, zoom=10)
    st.pydeck_chart(pdk.Deck(layers=[user_layer, hosp_layer], initial_view_state=view_state), use_container_width=True)

# -------------------- 범례(legend) --------------------
st.markdown("---")
st.markdown("### 범례 (진료과목 / 응급)")
legend_html = """
<div style='display:flex;flex-wrap:wrap;gap:8px;align-items:center'>
"""
# Build legend items from SPECIALTY_COLOR_MAP (select representative keys)
legend_items = ['응급실','내과','외과','치과','산부인과','소아청소년과','정형외과','정신과','한방','기타']
for key in legend_items:
    rgb = SPECIALTY_COLOR_MAP.get(key if key in SPECIALTY_COLOR_MAP else key.replace('실','')) if key in SPECIALTY_COLOR_MAP else SPECIALTY_COLOR_MAP['기타']
    if rgb is None:
        # find by substring
        found = None
        for k,v in SPECIALTY_COLOR_MAP.items():
            if key in k:
                found = v; break
        rgb = found or SPECIALTY_COLOR_MAP['기타']
    legend_html += f"<div style='display:flex;align-items:center;gap:6px;margin-right:12px'><div style='width:18px;height:18px;background:rgb({rgb[0]},{rgb[1]},{rgb[2]});border-radius:3px;'></div><div style='font-size:14px'>{key}</div></div>"
legend_html += "</div>"
st.markdown(legend_html, unsafe_allow_html=True)

st.markdown("---")
st.caption("앱: GitHub raw CSV 로드, 장소검색은 외부 geocoding 사용(geopy). CSV 컬럼명이 다르면 자동 감지 로직을 확인하세요.")
