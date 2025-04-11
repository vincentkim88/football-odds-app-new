
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import pytz
import matplotlib.pyplot as plt

# === 配置 ===
API_KEY = "114914-zmAWKLNAHcge1r"
TIMEZONE = pytz.timezone("Asia/Shanghai")  # UTC+8
REFRESH_INTERVAL = 60 * 1000  # 每 60 秒自动刷新（单位：毫秒）

# === 自动刷新页面 ===
st_autorefresh(interval=REFRESH_INTERVAL, key="auto-refresh")

# === 获取所有比赛 ===
def get_all_matches(sport_id=1):
    url = f"https://betsapi.com/api/v1/event/all?sport_id={sport_id}&token={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("results", [])
    return []

# === 获取赔率 ===
def get_odds(event_id):
    url = f"https://betsapi.com/api/v1/event/odds?token={API_KEY}&event_id={event_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("results", [])
    return []

# === 筛选公平盘口 ===
def is_fair_handicap_ah(value):
    try:
        h = float(value)
        return -2.5 <= h <= 2.5
    except:
        return False

def is_fair_handicap_ou(value):
    try:
        h = float(value)
        return 1.5 <= h <= 4.5
    except:
        return False

# === 队伍 logo ===
def team_logo(image_id):
    if image_id:
        return f"https://cdn.betsapi.com/team/{image_id}.png"
    return None

# === 赔率走势图 ===
def plot_odds_trend(odds_data, book_name="Bet365", odds_type="1x2"):
    records = [o for o in odds_data if o.get("book", {}).get("name") == book_name and o.get("type") == odds_type]
    if not records or not records[0].get("odds"):
        st.warning("暂无赔率走势数据")
        return

    timestamps = []
    home_odds, draw_odds, away_odds = [], [], []

    for record in records[0]["odds"]:
        ts = datetime.fromtimestamp(record["time"])
        timestamps.append(ts)
        home_odds.append(record.get("home"))
        draw_odds.append(record.get("draw"))
        away_odds.append(record.get("away"))

    fig, ax = plt.subplots()
    ax.plot(timestamps, home_odds, label="主胜", marker="o")
    ax.plot(timestamps, draw_odds, label="平局", marker="o")
    ax.plot(timestamps, away_odds, label="客胜", marker="o")
    ax.set_title(f"{book_name} 胜平负赔率变化")
    ax.set_xlabel("时间")
    ax.set_ylabel("赔率")
    ax.legend()
    st.pyplot(fig)

# === 展示赔率 ===
def show_odds(event_id):
    all_odds = get_odds(event_id)
    wanted_bookmakers = ["Bet365", "SBOBET", "Pinnacle"]

    odds_by_type = {
        "1x2": [],
        "asian_handicap": [],
        "over_under": []
    }

    for item in all_odds:
        book = item.get("book", {}).get("name")
        odds_type = item.get("type")

        if book in wanted_bookmakers and odds_type in odds_by_type:
            odds_data = item.get("odds", [])
            if not odds_data:
                continue

            if odds_type == "1x2":
                last = odds_data[-1]
                odds_by_type["1x2"].append({
                    "公司": book,
                    "主胜": last.get("home", "-"),
                    "平局": last.get("draw", "-"),
                    "客胜": last.get("away", "-")
                })

            elif odds_type == "asian_handicap":
                filtered = [o for o in odds_data if is_fair_handicap_ah(o.get("handicap"))]
                for o in filtered[-3:]:
                    odds_by_type["asian_handicap"].append({
                        "公司": book,
                        "盘口": o.get("handicap", "-"),
                        "主队赔率": o.get("home", "-"),
                        "客队赔率": o.get("away", "-")
                    })

            elif odds_type == "over_under":
                filtered = [o for o in odds_data if is_fair_handicap_ou(o.get("handicap"))]
                for o in filtered[-3:]:
                    odds_by_type["over_under"].append({
                        "公司": book,
                        "盘口": o.get("handicap", "-"),
                        "大球赔率": o.get("over", "-"),
                        "小球赔率": o.get("under", "-")
                    })

    st.markdown("#### 🧲 胜平负（1X2）")
    if odds_by_type["1x2"]:
        st.table(pd.DataFrame(odds_by_type["1x2"]))
        if st.checkbox("📈 显示 Bet365 胜平负赔率走势图", key=f"trend_{event_id}"):
            plot_odds_trend(all_odds, book_name="Bet365", odds_type="1x2")
    else:
        st.info("暂无 1X2 赔率数据")

    st.markdown("#### 🔲 亚盘（Asian Handicap）")
    if odds_by_type["asian_handicap"]:
        st.table(pd.DataFrame(odds_by_type["asian_handicap"]))
    else:
        st.info("暂无 公平盘口 亚盘 数据")

    st.markdown("#### ⚖️ 大小球（Over/Under）")
    if odds_by_type["over_under"]:
        st.table(pd.DataFrame(odds_by_type["over_under"]))
    else:
        st.info("暂无 公平盘口 大小球 数据")

# === 主函数 ===
def main():
    st.set_page_config(page_title="足球赛程 - BetsAPI", layout="wide")
    st.title("⚽ 足球赛程 & 实时赔率展示")

    with st.spinner("正在加载比赛数据..."):
        matches = get_all_matches()

    if matches:
        df = pd.json_normalize(matches)
        df = df[["id", "time", "league.name", "league.cc", "league.logo", "home.name", "home.image_id", "away.name", "away.image_id"]]
        df.columns = ["event_id", "时间", "联赛", "国家代码", "联赛LOGO", "主队", "主队LOGO", "客队", "客队LOGO"]
        df["时间"] = pd.to_datetime(df["时间"], unit='s').dt.tz_localize('UTC').dt.tz_convert(TIMEZONE)

        st.sidebar.header("🔍 筛选")
        countries = sorted(df["国家代码"].dropna().unique())
        leagues = sorted(df["联赛"].dropna().unique())
        selected_country = st.sidebar.selectbox("国家", ["全部"] + countries)
        selected_league = st.sidebar.selectbox("联赛", ["全部"] + leagues)
        time_filter = st.sidebar.radio("比赛时间", ["全部", "今天", "明天"])

        now = datetime.now(TIMEZONE)
        if selected_country != "全部":
            df = df[df["国家代码"] == selected_country]
        if selected_league != "全部":
            df = df[df["联赛"] == selected_league]
        if time_filter == "今天":
            start = now.replace(hour=0, minute=0, second=0)
            end = start + timedelta(days=1)
            df = df[(df["时间"] >= start) & (df["时间"] < end)]
        elif time_filter == "明天":
            start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
            end = start + timedelta(days=1)
            df = df[(df["时间"] >= start) & (df["时间"] < end)]

        for _, row in df.iterrows():
            with st.container():
                cols = st.columns([1, 5, 2, 1, 2])
                with cols[0]:
                    st.image(row["联赛LOGO"], width=40)
                with cols[1]:
                    st.markdown(f"**{row['联赛']}**（{row['国家代码']}）")
                    st.markdown(f"🕒 {row['时间'].strftime('%Y-%m-%d %H:%M')} (UTC+8)")
                with cols[2]:
                    st.image(team_logo(row["主队LOGO"]), width=40)
                    st.markdown(f"**{row['主队']}**")
                with cols[3]:
                    st.markdown("🆚")
                with cols[4]:
                    st.image(team_logo(row["客队LOGO"]), width=40)
                    st.markdown(f"**{row['客队']}**")
                with st.expander("📈 查看赔率（Bet365 / SBO / Pinnacle）"):
                    show_odds(row["event_id"])

    else:
        st.warning("⚠️ 未获取到比赛数据。请稍后再试。")

if __name__ == "__main__":
    main()
