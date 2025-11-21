import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from haversine import haversine, Unit
import requests

st.title("🏨 서울 호텔 + 주변 관광지 시각화 (JSON 데이터)")

# 🔑 API Key
api_key = "f0e46463ccf90abd0defd9c79c8568e922e07a835961b1676cdb2065ecc23494"

# -------------------
# 1) 호텔 정보 가져오기
# -------------------
@st.cache_data(ttl=3600)
def get_hotels(api_key):
    url = "http://apis.data.go.kr/B551011/KorService2/searchStay2"
    params = {
        "ServiceKey": api_key,
        "numOfRows": 50,
        "pageNo": 1,
        "MobileOS": "ETC",
        "MobileApp": "hotel_analysis",
        "arrange": "A",
        "_type": "json",
        "areaCode": 1  # 서울
    }
    res = requests.get(url, params=params, timeout=10)
    data = res.json()
    items = data['response']['body']['items']['item']
    df = pd.DataFrame(items)
    for col in ['title','mapx','mapy']:
        if col not in df.columns:
            df[col] = None
    df = df[['title','mapx','mapy']].rename(columns={'title':'name','mapx':'lng','mapy':'lat'})
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lng'] = pd.to_numeric(df['lng'], errors='coerce')
    df = df.dropna(subset=['lat','lng'])
    df['price'] = np.random.randint(150000, 300000, size=len(df))
    df['rating'] = np.random.uniform(3.0,5.0, size=len(df)).round(1)
    return df

hotels_df = get_hotels(api_key)

# -------------------
# 2) 호텔 선택
# -------------------
hotel_names = hotels_df['name'].tolist()
selected_hotel = st.selectbox("호텔 선택", hotel_names)
hotel_info = hotels_df[hotels_df['name']==selected_hotel].iloc[0]

# -------------------
# 3) JSON 관광지 파일 선택 및 불러오기
# -------------------
tourist_file = st.selectbox("관광지 데이터 파일 선택", [
    "서울시 관광거리 정보 (한국어)(2015년).json",
    "서울시 종로구 관광데이터 정보 (한국어).json"
])

@st.cache_data(ttl=3600)
def load_tourist_json(json_file):
    df = pd.read_json(json_file)
    
    # 서울시 관광거리 정보 (한국어)(2015년)
    if '중심 좌표 X' in df.columns and '중심 좌표 Y' in df.columns and '최종 표기명' in df.columns:
        df['lng'] = pd.to_numeric(df['중심 좌표 X'], errors='coerce')
        df['lat'] = pd.to_numeric(df['중심 좌표 Y'], errors='coerce')
        df['name'] = df['최종 표기명']
    
    # 서울시 종로구 관광데이터 정보 (한국어)
    elif 'X 좌표' in df.columns and 'Y 좌표' in df.columns and '명칭' in df.columns:
        df['lng'] = pd.to_numeric(df['X 좌표'], errors='coerce')
        df['lat'] = pd.to_numeric(df['Y 좌표'], errors='coerce')
        df['name'] = df['명칭']
    
    df = df.dropna(subset=['lat','lng'])
    return df[['name','lat','lng']]

tourist_df = load_tourist_json(tourist_file)

# -------------------
# 4) 호텔 반경 내 관광지 필터링
# -------------------
radius_m = st.slider("관광지 반경 (m)", 500, 2000, 1000, step=100)

def get_nearby_tourist(hotel_lat, hotel_lng, tourist_df, radius_m):
    nearby = []
    for idx, row in tourist_df.iterrows():
        distance = haversine((hotel_lat, hotel_lng), (row['lat'], row['lng']), unit=Unit.METERS)
        if distance <= radius_m:
            nearby.append(row)
    return pd.DataFrame(nearby)

nearby_tourist_df = get_nearby_tourist(hotel_info['lat'], hotel_info['lng'], tourist_df, radius_m)

# -------------------
# 5) 지도 시각화
# -------------------
m = folium.Map(location=[hotel_info['lat'], hotel_info['lng']], zoom_start=15)

# 호텔 마커
folium.Marker(
    location=[hotel_info['lat'], hotel_info['lng']],
    popup=f"{hotel_info['name']} | 가격: {hotel_info['price']} | 별점: {hotel_info['rating']}",
    icon=folium.Icon(color='red', icon='hotel', prefix='fa')
).add_to(m)

# 관광지 마커
for idx, row in nearby_tourist_df.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lng']],
        radius=4,
        color='blue',
        fill=True,
        fill_opacity=0.7,
        popup=row['name']
    ).add_to(m)

st.subheader(f"{selected_hotel} 주변 관광지 지도")
st_folium(m, width=700, height=500, returned_objects=[])

# -------------------
# 6) 호텔 정보 + 관광지 목록
# -------------------
st.subheader("호텔 정보 및 주변 관광지")
st.write(f"**호텔명:** {hotel_info['name']}")
st.write(f"**가격:** {hotel_info['price']}원")
st.write(f"**별점:** {hotel_info['rating']}")
st.write(f"**주변 관광지 수:** {len(nearby_tourist_df)}")
st.dataframe(nearby_tourist_df[['name']])
