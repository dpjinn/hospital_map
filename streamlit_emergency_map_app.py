# streamlit_emergency_map_app.py
# 설명 (한국어):
# 이 Streamlit 앱은 업로드된 병원 CSV 파일(또는 같은 폴더의 hospitals.csv)을 읽어 지도에 표시하고,
# 사이드바(마크다운 섹션 포함)를 통해 지역, 시간, 요일, 병명으로 필터링할 수 있게 합니다.
# 필터 결과가 없을 경우 "가장 가까운 응급실"을 자동으로 안내합니다. 모든 UI는 한국어로 표시됩니다.
# 사용 방법:
# 1) 같은 폴더에 hospitals.csv 파일을 넣거나, 앱에서 CSV 파일을 업로드하세요.
# 2) Windows에서: 가상환경을 만들고 아래 명령으로 필요 패키지를 설치하세요.
#    pip install streamlit pandas pydeck
# 3) 앱 실행:
#    streamlit run streamlit_emergency_map_app.py
# GitHub 업로드: 이 파일과 hospitals.csv, requirements.txt(아래 내용)를 같은 저장소에 올리면 됩니다.
# requirements.txt (추천):
# streamlit
# pandas
# pydeck
# -----------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import math
from datetime import datetime

st.set_page_config(page_title="응급실/병원 지도", layout="wide")

# ------------------ 유틸리티 함수 ------------------
COMMON_LAT_KEYS = ['lat','latitude','y','위도','위도_','위도(위도)']
COMMON_LON_KEYS = ['lon','lng','longitude','x','경도','경도_','경도(경도)']
REGION_KEYS = ['지역','시군구','주소','addr','address','지역명']
NAME_KEYS = ['name','병원','상호','의료기관명','기관명']
TIME_KEYS = ['시간','영업시간','운영시간','open','hours']
WEEKDAY_KEYS = ['요일','영업요일','운영요일']
EMERGENCY_KEYS = ['응급','응급실','ER','emergency']


def detect_columns(df):
    cols_low = {c.lower(): c for c in df.columns}
    def find(keys):
        for k in keys:
            kl = k.lower()
            if kl in cols_low:
                return cols_low[kl]
        # try substring match
        for cname in df.columns:
            for k in keys:
                if k.lower() in cname.lower():
                    return cname
        return None

    lat_col = find(COMMON_LAT_KEYS)
    lon_col = find(COMMON_LON_KEYS)
    region_col = find(REGION_KEYS)
    name_col = find(NAME_KEYS)
    time_col = find(TIME_KEYS)
    weekday_col = find(WEEKDAY_KEYS)
    emergency_col = find(EMERGENCY_KEYS)
    return {
        'lat': lat_col,
        'lon': lon_col,
        'region': region_col,
        'name': name_col,
        'time': time_col,
        'weekday': weekday_col,
        'emergency': emergency_col
    }


def haversine(lat1, lon1, lat2, lon2):
    # all in degrees
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2*math.asin(math.sqrt(a))
    return R * c


def find_nearest(df, user_lat, user_lon, n=1):
    df = df.copy()
    df['__dist_km'] = df.apply(lambda r: haversine(user_lat, user_lon, r['__lat'], r['__lon']), axis=1)
    df = df.sort_values('__dist_km')
    return df.head(n)

# ------------------ 데이터 불러오기 ------------------
st.title("응급실/병원 지도 — Streamlit 앱 (한국어)")

uploaded = st.file_uploader('CSV 파일을 업로드하세요 (병원 정보 CSV). 파일이 없으면 오른쪽의 예시 파일을 사용하세요.', type=['csv'])

if uploaded is None:
    # try to load hospitals.csv from same folder
    try:
        df = pd.read_csv('병원데이터.csv', encoding='utf-8')
        st.info('로컬 파일 hospitals.csv를 불러왔습니다.')
    except Exception:
        try:
            # 마지막으로 시도: 제공된 경로(자동)가 있을 수 있음
            df = pd.read_csv('/mnt/data/23701ec3-7212-4608-9c43-4a9c1d3b6726.csv', encoding='utf-8')
            st.info('내부 제공 CSV를 불러왔습니다.')
        except Exception:
            st.warning('CSV 파일을 업로드하거나 프로젝트 폴더에 hospitals.csv를 놓아주세요.')
            st.stop()
else:
    df = pd.read_csv(uploaded)

# 기본 전처리
original_columns = list(df.columns)
cols = detect_columns(df)

# 시도: 위도/경도 컬럼을 찾아 숫자로 변환
if cols['lat'] and cols['lon']:
    df['__lat'] = pd.to_numeric(df[cols['lat']], errors='coerce')
    df['__lon'] = pd.to_numeric(df[cols['lon']], errors='coerce')
else:
    # 경우에 따라 주소만 있다면 간단히 중단 — 사용자가 업로드한 파일에 좌표가 필요합니다.
    st.error('데이터에 위도/경도 컬럼이 없습니다. 위도/경도(lat, lon) 컬럼이 필요합니다. 컬럼명이 다르면 CSV를 확인해주세요.')
    st.write('원래 컬럼명:', original_columns)
    st.stop()

# 이름/지역 컬럼 대체
name_col = cols['name'] if cols['name'] in df.columns else None
region_col = cols['region'] if cols['region'] in df.columns else None
emergency_col = cols['emergency'] if cols['emergency'] in df.columns else None

if name_col is None:
    # fallback: 첫 번째 문자열 컬럼
    str_cols = df.select_dtypes(include=['object']).columns.tolist()
    name_col = str_cols[0] if str_cols else None

# UI: 필터 사이드바 (마크다운 스타일로 그룹화)
st.sidebar.markdown('## 필터 (마크다운 섹션)')

# 사용자 위치 입력 (근처 검색을 위해 필요)
st.sidebar.markdown('### 내 위치 (거리 기준으로 가장 가까운 응급실 안내 시 사용)')
user_lat = st.sidebar.number_input('내 위도 (예: 37.5665)', value=37.5665, format="%.6f")
user_lon = st.sidebar.number_input('내 경도 (예: 126.9780)', value=126.9780, format="%.6f")

# 지역 필터
if region_col:
    regions = df[region_col].dropna().astype(str).unique().tolist()
    regions_sorted = sorted(regions)
    sel_region = st.sidebar.multiselect('지역 선택', options=regions_sorted, default=None)
else:
    sel_region = None

# 시간 필터 (단순한 텍스트 검색 기반)
st.sidebar.markdown('### 시간/요일 필터 (가능한 경우)')
if cols['time']:
    time_text = st.sidebar.text_input('시간 포함 텍스트 (예: 09:00-18:00 또는 "24시간")')
else:
    time_text = ''

if cols['weekday']:
    weekday_options = sorted(df[cols['weekday']].dropna().astype(str).unique().tolist())
    sel_weekdays = st.sidebar.multiselect('영업 요일 선택', options=weekday_options)
else:
    sel_weekdays = None

# 병명 검색
st.sidebar.markdown('### 병원/클리닉 검색')
hospital_search = st.sidebar.text_input('병원명 또는 키워드 입력')

# 필터 적용
working = df.copy()
if sel_region:
    # 일부 행의 주소/지역에 대해 포함 여부 검사
    working = working[working[region_col].astype(str).apply(lambda x: any(r in x for r in sel_region))]

if time_text and cols['time']:
    working = working[working[cols['time']].astype(str).str.contains(time_text, na=False)]

if sel_weekdays and cols['weekday']:
    working = working[working[cols['weekday']].astype(str).apply(lambda s: any(w in str(s) for w in sel_weekdays))]

if hospital_search:
    working = working[working[name_col].astype(str).str.contains(hospital_search, na=False)]

# 좌표 복사
working['__lat'] = pd.to_numeric(working['__lat'], errors='coerce')
working['__lon'] = pd.to_numeric(working['__lon'], errors='coerce')
working = working.dropna(subset=['__lat','__lon'])

# 결과 출력 영역
st.markdown('## 결과')
if len(working) > 0:
    st.markdown(f'### 필터에 맞는 병원: 총 {len(working)}곳')

    # 지도 표시 (pydeck)
    midpoint = (working['__lat'].mean(), working['__lon'].mean())
    st.markdown('#### 지도')
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=working.rename(columns={cols['name'] if cols['name'] else name_col: 'label'}).to_dict(orient='records'),
        get_position='[__lon, __lat]',
        get_radius=200,
        pickable=True,
        auto_highlight=True,
    )
    tooltip = {"html": "<b>{label}</b><br/>위도: {__lat}<br/>경도: {__lon}", "style": {"color": "#000000"}}
    view_state = pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=11)
    r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)
    st.pydeck_chart(r)

    # 테이블 출력
    with st.expander('목록 보기'):
        display_cols = [c for c in [name_col, region_col, cols['time'], cols['weekday'], emergency_col, '__lat', '__lon'] if c in working.columns]
        st.dataframe(working[display_cols].rename(columns=lambda x: x if x is not None else ''))

else:
    st.markdown('### 필터에 맞는 병원이 없습니다.')
    st.info('가장 가까운 응급실(응급실 키워드 기반)을 안내합니다.')
    # 우선 응급을 포함하는 행을 찾음
    df_search = df.copy()
    df_search['__lat'] = pd.to_numeric(df_search['__lat'], errors='coerce')
    df_search['__lon'] = pd.to_numeric(df_search['__lon'], errors='coerce')
    df_search = df_search.dropna(subset=['__lat','__lon'])

    # 응급실 판단: emergency_col에 포함되거나 다른 컬럼에서 '응급' 포함
    candidates = pd.DataFrame()
    if emergency_col:
        candidates = df_search[df_search[emergency_col].astype(str).str.contains('응급|응급실|ER|Emergency', case=False, na=False)]
    if candidates.empty:
        # 다른 컬럼에서 찾아보기
        for c in df_search.columns:
            candidates = df_search[df_search[c].astype(str).str.contains('응급실|응급|ER|Emergency', case=False, na=False)]
            if not candidates.empty:
                break

    if candidates.empty:
        st.warning('명시적 응급실 표시가 없습니다. 모든 병원 중에서 가장 가까운 곳을 안내합니다.')
        nearest = find_nearest(df_search.rename(columns={'__lat': '__lat', '__lon': '__lon'}), user_lat, user_lon, n=3)
    else:
        nearest = find_nearest(candidates.rename(columns={'__lat': '__lat', '__lon': '__lon'}), user_lat, user_lon, n=3)

    st.markdown('#### 가장 가까운 응급실/병원')
    for idx, row in nearest.iterrows():
        label = row[name_col] if name_col in row and pd.notna(row[name_col]) else '이름 없음'
        dist = row['__dist_km']
        st.markdown(f"- **{label}** — 거리: {dist:.2f} km — 위도: {row['__lat']:.6f}, 경도: {row['__lon']:.6f}")

    # 지도: 사용자 위치 + nearest markers
    map_df = nearest.copy()
    midpoint = (map_df['__lat'].mean(), map_df['__lon'].mean())
    st.markdown('#### 지도 (내 위치 + 안내 병원)')
    # 사용자 위치 레이어
    user_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{'__lat': user_lat, '__lon': user_lon, 'label': '내 위치'}],
        get_position='[__lon, __lat]',
        get_radius=300,
        pickable=True,
        auto_highlight=True,
    )
    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df.to_dict(orient='records'),
        get_position='[__lon, __lat]',
        get_radius=300,
        pickable=True,
        auto_highlight=True,
    )
    view_state = pdk.ViewState(latitude=(user_lat+midpoint[0])/2, longitude=(user_lon+midpoint[1])/2, zoom=11)
    r = pdk.Deck(layers=[user_layer, hospital_layer], initial_view_state=view_state,
                tooltip={"html": "<b>{label}</b><br/>거리: {__dist_km} km<br/>위도: {__lat}<br/>경도: {__lon}", "style": {"color": "#000000"}})
    st.pydeck_chart(r)

st.markdown('---')
st.markdown('앱 사용 팁: CSV에 위도(lat)/경도(lon) 컬럼이 정확히 있어야 지도 기능이 정상 작동합니다. 컬럼명이 다르면 CSV를 열어 컬럼명을 확인하거나 파일 업로드 후 `원래 컬럼명`을 확인하세요.')

# 끝
