# -*- coding: utf-8 -*-
"""
app.py

❄️ 한국도로교통공단 결빙 교통사고 다발지역 대시보드

- 연도별, 지역별 결빙 교통사고 다발지역을 
  공공데이터포털 OpenAPI로 조회·시각화합니다.
"""
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px

# 페이지 설정
st.set_page_config(
    page_title="❄️ 결빙 교통사고 다발지역 대시보드",
    page_icon="❄️",
    layout="wide"
)

# Decoding된 일반 인증키
SERVICE_KEY = (
    "jUxxEMTFyxsIT2rt2P8JBO9y0EmFT9mx1zNPb31XLX27rFNH12NQ"
    "+6+ZLqqvW6k/ffQ5ZOOYzzcSo0Fq4u3Lfg=="
)

@st.cache_data
def load_freezing_data(year: str, sido: str = "", gugun: str = "") -> pd.DataFrame:
    """
    공공데이터포털 '결빙 교통사고 다발지역' API 호출 후
    DataFrame으로 변환·전처리합니다.
    """
    url = "http://apis.data.go.kr/B552061/frequentzoneFreezing/getRestFrequentzoneFreezing"
    params = {
        "serviceKey": SERVICE_KEY,
        "searchYearCd": year,
        "siDo": sido,
        "guGun": gugun,
        "type": "json",
        "numOfRows": 500,
        "pageNo": 1
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    js = resp.json()
    items = js.get("items", [])
    # items: list of {"item": {...}}
    records = [rec["item"] for rec in items if "item" in rec]
    df = pd.DataFrame(records)
    if df.empty:
        return df

    # 칼럼 정제 및 변환
    # 위도/경도
    df["la_crd"] = pd.to_numeric(df["la_crd"], errors="coerce")
    df["lo_crd"] = pd.to_numeric(df["lo_crd"], errors="coerce")
    # 사고 건수
    df["occrrnc_cnt"] = pd.to_numeric(df["occrrnc_cnt"], errors="coerce")
    df["caslt_cnt"]    = pd.to_numeric(df["caslt_cnt"],    errors="coerce")
    # 시도명 추출
    df["sido"] = df["sido_sgg_nm"].str.split().str[0]
    # 결측 제거
    df = df.dropna(subset=["la_crd", "lo_crd", "occrrnc_cnt"])
    return df

def main():
    st.title("❄️ 결빙 교통사고 다발지역 대시보드")
    st.markdown(
        "한국도로교통공단 제공 결빙 교통사고 다발지역 정보를\n"
        "연도·지역별로 조회하고 지도·차트로 시각화합니다."
    )

    # 사이드바: 연도 & 시도·시군구 필터
    years = [str(y) for y in range(2015, 2024)][::-1]
    year = st.sidebar.selectbox("📅 기준년도 선택", years, index=0)
    df = load_freezing_data(year)

    if df.empty:
        st.warning("API 호출 결과 데이터가 없습니다.")
        st.stop()

    # 시도 필터
    sido_list = ["전체"] + sorted(df["sido"].unique().tolist())
    sel_sido = st.sidebar.selectbox("🏙️ 시도 필터", sido_list)
    if sel_sido != "전체":
        df = df[df["sido"] == sel_sido]

    # 시군구 필터
    gugun_list = ["전체"] + sorted(
        df["sido_sgg_nm"].loc[df["sido"] == sel_sido].unique().tolist()
    ) if sel_sido != "전체" else ["전체"]
    sel_gugun = st.sidebar.selectbox("🗺️ 시군구 필터", gugun_list)
    if sel_gugun != "전체":
        df = df[df["sido_sgg_nm"] == sel_gugun]

    # 요약 지표
    st.subheader("📊 요약 지표")
    col1, col2, col3 = st.columns(3)
    col1.metric("🔢 건수(레코드)", f"{len(df):,}")
    col2.metric("❄️ 평균 사고 건수", f"{df['occrrnc_cnt'].mean():.1f}")
    col3.metric("🤕 평균 부상자 수", f"{df['caslt_cnt'].mean():.1f}")

    # 지도 시각화
    st.subheader("🗺️ 결빙 사고 다발지역 지도")
    fig_map = px.scatter_mapbox(
        df,
        lat="la_crd",
        lon="lo_crd",
        size="occrrnc_cnt",
        color="occrrnc_cnt",
        hover_name="sido_sgg_nm",
        hover_data=["occrrnc_cnt", "caslt_cnt"],
        color_continuous_scale="blues",
        size_max=20,
        zoom=6,
        mapbox_style="carto-positron",
        title=f"{year}년 결빙 교통사고 다발지역"
    )
    st.plotly_chart(fig_map, use_container_width=True, theme=None)

    # Top 10 사고 건수 지역
    st.subheader("🔥 사고 건수 Top 10 지역")
    top10 = df.nlargest(10, "occrrnc_cnt").reset_index(drop=True)
    st.dataframe(
        top10[["sido_sgg_nm", "occrrnc_cnt", "caslt_cnt"]],
        use_container_width=True
    )

    # 히트맵: 시도별 사고 건수
    st.subheader("🌡️ 시도별 결빙 사고 건수 분포")
    heat_df = df.groupby("sido")["occrrnc_cnt"].sum().reset_index()
    fig_heat = px.density_heatmap(
        heat_df, x="sido", y="occrrnc_cnt",
        color_continuous_scale="Viridis",
        labels={"sido": "시도", "occrrnc_cnt": "사고 건수"},
        height=350
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.subheader("📈 시도별 사고 건수 비교 차트")
    fig_bar = px.bar(
        heat_df.sort_values("occrrnc_cnt", ascending=False),
        x="sido", y="occrrnc_cnt",
        labels={"sido": "시도", "occrrnc_cnt": "사고 건수"},
        color="occrrnc_cnt", color_continuous_scale="Blues"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # 인사이트
    st.subheader("💡 인사이트")
    st.markdown("""
    - 결빙 교통사고는 주로 내륙 북부·산간 지역에서 집중 발생합니다.
    - 사고 건수가 많은 상위 지역을 중심으로 제설·제빙 작업 강화가 필요합니다.
    - 시도별 사고 건수와 부상자 수를 비교하여 고위험 구간을 선제 대응하세요.
    """)

if __name__ == "__main__":
    main()

