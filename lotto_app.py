import streamlit as st
import pandas as pd
import numpy as np
import requests
import os

st.set_page_config(page_title="로또 분석 추천기", layout="centered")
st.title("🎯로또 분석 기반 추천 번호 생성기")

# --- 로또 API 불러오기 ---
def get_lotto_data(drw_no):
    url = f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={drw_no}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        if data['returnValue'] == 'success':
            return {
                "회차": data['drwNo'],
                "번호1": data['drwtNo1'],
                "번호2": data['drwtNo2'],
                "번호3": data['drwtNo3'],
                "번호4": data['drwtNo4'],
                "번호5": data['drwtNo5'],
                "번호6": data['drwtNo6'],
                "보너스": data['bnusNo'],
                "추첨일": data['drwNoDate']
            }
    return None

# --- 전체 회차 데이터 불러오기 (로컬 캐싱 + 최신 회차 병합 + 진행률 표시) ---
@st.cache_data
def get_all_lotto_data():
    cache_file = "lotto_data_cache.csv"

    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, parse_dates=["추첨일"])
        latest_cached_round = df["회차"].max()
    else:
        df = pd.DataFrame()
        latest_cached_round = 0

    updated_results = []
    total_to_check = 1300 - latest_cached_round
    progress_bar = st.progress(0, text="최신 회차 확인 중...")

    for i, round_no in enumerate(range(latest_cached_round + 1, 1300)):
        result = get_lotto_data(round_no)
        if result:
            result["추첨일"] = pd.to_datetime(result["추첨일"])
            updated_results.append(result)
        else:
            break
        progress_bar.progress((i + 1) / total_to_check, text=f"{round_no}회차 확인 중...")

    if updated_results:
        df_new = pd.DataFrame(updated_results)
        df = pd.concat([df, df_new], ignore_index=True)
        df.to_csv(cache_file, index=False)

    progress_bar.empty()
    return df

# --- 날짜 선택 UI로 변경 ---
st.subheader("1️⃣ 학습 데이터 날짜 선택")
df_all = get_all_lotto_data()
df_all = df_all.sort_values("추첨일", ascending=False).reset_index(drop=True)
df_all["표시용"] = df_all["추첨일"].dt.date.astype(str) + " (" + df_all["회차"].astype(str) + "회차)"

# 기본값: 최신 회차 기준 5개 전 날짜
default_end_index = 0
default_start_index = min(5, len(df_all) - 1)

col1, col2 = st.columns(2)
with col1:
    selected_start_display = st.selectbox("시작일 선택", options=df_all["표시용"], index=default_start_index)
with col2:
    selected_end_display = st.selectbox("종료일 선택", options=df_all["표시용"], index=default_end_index)

selected_start_date = df_all[df_all["표시용"] == selected_start_display]["추첨일"].dt.date.values[0]
selected_end_date = df_all[df_all["표시용"] == selected_end_display]["추첨일"].dt.date.values[0]

if selected_start_date > selected_end_date:
    st.error("시작일은 종료일보다 같거나 이전이어야 합니다.")
    st.stop()

# --- 데이터 필터링 (기본값으로도 동작하도록 분리) ---
filtered_df = df_all[(df_all["추첨일"].dt.date >= selected_start_date) & (df_all["추첨일"].dt.date <= selected_end_date)]

# --- 데이터 로딩 버튼 ---
st.subheader("2️⃣ 로또 데이터 불러오기")
if st.button("📥 데이터 불러오기"):
    st.success(f"{len(filtered_df)}개 회차가 선택되었습니다.")

# --- 데이터 항상 표시 ---
if not filtered_df.empty:
    display_df = filtered_df.copy()
    display_df = display_df[["표시용", "번호1", "번호2", "번호3", "번호4", "번호5", "번호6", "보너스"]]
    display_df = display_df.rename(columns={"표시용": "추첨일"})
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=240)
    df = filtered_df.copy()  # 이후 분석용

    # --- 세트 선택 버튼 ---
    st.subheader("🎯 추천 번호 세트 선택")
    col_set1, col_set2, col_set3, col_set4 = st.columns(4)
    with col_set1:
        show_set1 = st.button("세트 1")
    with col_set2:
        show_set2 = st.button("세트 2")
    with col_set3:
        show_set3 = st.button("세트 3")
    with col_set4:
        show_set4 = st.button("세트 4")
        if show_set4:
            st.session_state['show_set4'] = True
        elif show_set1 or show_set2 or show_set3:
            st.session_state['show_set4'] = False



    if show_set1:
        st.markdown("#### 🎲 세트 1 추천 번호")
        "세트1 : 기초 통계 기반"
        def generate_set1_recommendations(df, num_sets=10):
            numbers = df[[f"번호{i}" for i in range(1, 7)]].values.flatten()
            top_numbers = pd.Series(numbers).value_counts().nlargest(20).index.tolist()

            recommendations = []
            for _ in range(num_sets):
                picks = sorted(np.random.choice(top_numbers, size=6, replace=False).tolist())
                recommendations.append(picks)
            return recommendations

        results = generate_set1_recommendations(df)
        for i, rec in enumerate(results, 1):
            st.markdown(
                "<div style='text-align:center; font-size:18px; font-weight:normal; padding:6px 0; word-spacing:24px;'>" +
                " ".join([str(num) for num in rec]) +
                "</div>",
                unsafe_allow_html=True
            )

    if show_set2:
        st.markdown("#### 🔍 세트 2 추천 번호")
        "세트2 : 패턴 적용 (비극단적)"
        def generate_set2_recommendations(df, num_sets=10):
            # 밀집도 기반 추천: 각 회차 번호의 범위 계산 후, 평균 범위 기준 유사한 조합 생성
            all_numbers = df[[f"번호{i}" for i in range(1, 7)]].values.tolist()
            ranges = [max(row) - min(row) for row in all_numbers]
            avg_range = np.mean(ranges)

            number_pool = list(range(1, 46))
            recommendations = []
            for _ in range(num_sets):
                while True:
                    candidate = sorted(np.random.choice(number_pool, size=6, replace=False).tolist())
                    if abs(max(candidate) - min(candidate) - avg_range) <= 3:
                        recommendations.append(candidate)
                        break
            return recommendations

        results = generate_set2_recommendations(df)
        for i, rec in enumerate(results, 1):
            st.markdown(
                "<div style='text-align:center; font-size:18px; font-weight:normal; padding:6px 0; word-spacing:24px;'>" +
                " ".join([str(num) for num in rec]) +
                "</div>",
                unsafe_allow_html=True
            )
    if show_set3:
        st.markdown("#### 📊 세트 3 추천 번호")
        "세트3 : 패턴 적용 (극단적)"
        def generate_set3_recommendations(df, num_sets=10):
            # 극단적 밀집 구조 허용: 범위가 매우 좁거나 번호대가 몰려있는 조합 허용
            number_pool = list(range(1, 46))
            recommendations = []
            for _ in range(num_sets):
                while True:
                    candidate = sorted(np.random.choice(number_pool, size=6, replace=False).tolist())
                    range_val = max(candidate) - min(candidate)
                    if range_val <= 15:  # 매우 좁은 범위의 밀집 구조
                        recommendations.append(candidate)
                        break
            return recommendations

        results = generate_set3_recommendations(df)
        for i, rec in enumerate(results, 1):
            st.markdown(
                "<div style='text-align:center; font-size:18px; font-weight:normal; padding:6px 0; word-spacing:24px;'>" +
                " ".join([str(num) for num in rec]) +
                "</div>",
                unsafe_allow_html=True
            )

    if 'show_set4' not in st.session_state:
        st.session_state['show_set4'] = False

    if st.session_state.get('show_set4', False):
        st.markdown("#### 🔮 사주 기반 추천 번호")


        def generate_saju_numbers(birth_date, birth_hour=0):
            heavenly_stems = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
            earthly_branches = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
            five_elements = {
                "목": [3, 8, 13, 18, 23],
                "화": [2, 7, 12, 17, 22],
                "토": [5, 10, 15, 20, 25],
                "금": [4, 9, 14, 19, 24],
                "수": [1, 6, 11, 16, 21]
            }
            hour_to_branch = ["자", "축", "인", "인", "묘", "묘", "진", "진", "사", "사", "오", "오",
                              "미", "미", "신", "신", "유", "유", "술", "술", "해", "해", "자", "자"]

            base = birth_date.year * 10000 + birth_date.month * 100 + birth_date.day
            gan_index = base % 10
            ji_index = base % 12
            gan = heavenly_stems[gan_index]
            ji = earthly_branches[ji_index]
            si = hour_to_branch[birth_hour % 24]  # 시지

            gan_element_map = {
                "갑": "목", "을": "목", "병": "화", "정": "화",
                "무": "토", "기": "토", "경": "금", "신": "금",
                "임": "수", "계": "수"
            }
            ji_element_map = {
                "자": "수", "축": "토", "인": "목", "묘": "목",
                "진": "토", "사": "화", "오": "화", "미": "토",
                "신": "금", "유": "금", "술": "토", "해": "수"
            }

            gan_elem = gan_element_map[gan]
            ji_elem = ji_element_map[ji]
            si_elem = ji_element_map[si]

            # 전체 오행 분포 분석
            elements = [gan_elem, ji_elem, si_elem]
            counts = {elem: elements.count(elem) for elem in five_elements}

            # 부족한 오행에 가중치 부여
            total = sum(counts.values())
            weights = {elem: (3 - counts[elem]) / 3 for elem in five_elements}  # 부족할수록 높음

            weighted_pool = []
            for elem in five_elements:
                w = weights[elem]
                weighted_pool += five_elements[elem] * int(w * 10 + 1)

            result = []
            while len(result) < 6:
                pick = np.random.choice(weighted_pool)
                if pick not in result:
                    result.append(pick)

            return sorted(result)


        with st.form("사주입력"):
            col1, col2 = st.columns(2)
            with col1:
                birth_date_str = st.text_input("생년월일", placeholder="YYYY-MM-DD")
            with col2:
                birth_hour = st.number_input("출생 시간 (0~23시)", min_value=0, max_value=23, value=0, step=1)
            submitted = st.form_submit_button("추천 번호 보기")

            if submitted:
                try:
                    birth_date = pd.to_datetime(birth_date_str).date()
                    saju_recommended = generate_saju_numbers(birth_date, birth_hour)
                    st.markdown("**사주 기반 추천 숫자군:**")
                    st.markdown(
                        "<div style='text-align:center; font-size:18px; font-weight:normal; padding:6px 0; word-spacing:24px;'>" +
                        " ".join([str(num) for num in saju_recommended]) +
                        "</div>",
                        unsafe_allow_html=True
                    )
                except:
                    st.error("날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식으로 입력해 주세요.")
