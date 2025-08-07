import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import streamlit.components.v1 as components
import unicodedata

def normalize(text):
    return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode().lower()

st.set_page_config(page_title="Infomõjutuse artiklid", layout="wide")

if "search_override" not in st.session_state:
    st.session_state.search_override = None

# --- TIITEL ---
st.markdown(
    "<h1 style='text-align: center; color: #2C3E50;'>Infomõjutuse kajastuste otsing</h1>",
    unsafe_allow_html=True,
)

# --- ANDMEBAAS ---
conn = sqlite3.connect("infomojutus.db")
df = pd.read_sql_query("SELECT * FROM artiklid", conn)
df["kuupäev"] = pd.to_datetime(df["kuupäev"], format="%d.%m.%Y", errors="coerce")
df = df.sort_values(by="kuupäev", ascending=False)  # ← see lisab vaikimisi järjestuse uuemast vanimani


# --- KOLM JAOTUST ---
vasak, keskmine, parem = st.columns([1, 2, 1])

# --- VASAKPOOLNE VEERG (Filtrid + Statistika) ---
with vasak:
    st.markdown("## 🧰 Filtrid")
    teema_valik = st.multiselect("🎯 Vali teema:", sorted(df["teema"].dropna().unique()))
    min_kuup = df["kuupäev"].min()
    max_kuup = df["kuupäev"].max()
    kuup_range = st.date_input("📆 Vali kuupäevavahemik:", [min_kuup, max_kuup])
    raw_otsing = st.text_input("🔎 Otsi sõna järgi:", placeholder="nt. Ukraina, NATO, propaganda...")
    otsing = raw_otsing if st.session_state.search_override is None else st.session_state.search_override
    st.session_state.search_override = None


    st.markdown("---")
    st.markdown(f"**📄 Kirjeid kokku:** `{len(df)}`")
    st.markdown(f"**🧩 Erinevaid teemasid:** `{df['teema'].nunique()}`")

    st.markdown("### 🗂 Teemade jaotus:")
    teema_arvud = df["teema"].value_counts()
    for teema, arv in teema_arvud.items():
        if arv >= 5:
            st.markdown(f"- {teema}: {arv}")

# --- FILTRID ---
filtered_df = df.copy()


if teema_valik:
    filtered_df = filtered_df[filtered_df["teema"].isin(teema_valik)]

if len(kuup_range) == 2:
    start_date, end_date = kuup_range
    filtered_df = filtered_df[
        (filtered_df["kuupäev"] >= pd.to_datetime(start_date)) &
        (filtered_df["kuupäev"] <= pd.to_datetime(end_date))
    ]


if otsing:
    # Eemaldame jutumärgid, teeme väiketäheks ja normaliseerime (nt š → s)

    otsing_clean = (
    otsing.replace('"', '')
          .replace("'", "")
          .replace("“", "")
          .replace("”", "")
    )
    keywords = [normalize(k.strip()) for k in otsing_clean.split(" OR ")]


    def contains_any_keyword(row):
        row_text = normalize(str(row.values))
        return any(k in row_text for k in keywords)

    filtered_df = filtered_df[filtered_df.apply(contains_any_keyword, axis=1)]


filtered_df["kuupäev"] = filtered_df["kuupäev"].dt.strftime("%d.%m.%Y")

# --- KESKMINE VEERG (Artiklid) ---
with keskmine:
    st.markdown("### 📑 Leitud artiklid")

    def make_clickable(row):
        return f'<a href="{row.link}" target="_blank" style="color:#2980B9; text-decoration:none;">{row.pealkiri}</a>'

    # Klikitav pealkiri
    filtered_df["pealkiri"] = filtered_df.apply(make_clickable, axis=1)

    # Tagame, et vajalikud veerud on olemas
    for col in ["kuupäev", "pealkiri", "allikas", "juhtloik"]:
        if col not in filtered_df.columns:
            filtered_df[col] = ""

    # Ainult soovitud veerud
    filtered_df_display = filtered_df[["kuupäev", "pealkiri", "allikas", "juhtloik"]].copy()

    # CSS stiil allikas-veeru kitsendamiseks
    st.markdown(
        """
        <style>
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        th, td {
            padding: 8px 12px;
            border-bottom: 1px solid #ddd;
            text-align: left;
            vertical-align: top;
        }
        td.allikas-col {
            max-width: 150px;
            width: 150px;
            word-wrap: break-word;
            white-space: normal;
        }
        tr:hover {background-color: #f5f5f5;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Loome HTML tabeli käsitsi
    html_rows = []
    for _, row in filtered_df_display.iterrows():
        html_rows.append(f"""
            <tr>
                <td>{row['kuupäev']}</td>
                <td>{row['pealkiri']}</td>
                <td class="allikas-col">{row['allikas']}</td>
                <td>{row['juhtloik']}</td>
            </tr>
        """)

    html_table = f"""
    <html>
    <head>
    <style>
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th, td {{
            padding: 8px 12px;
            border-bottom: 1px solid #ddd;
            text-align: left;
            vertical-align: top;
        }}
        td.allikas-col {{
            max-width: 150px;
            width: 150px;
            word-wrap: break-word;
            white-space: normal;
        }}
        tr:hover {{background-color: #f5f5f5;}}
    </style>
    </head>
    <body>
    <table>
        <thead>
            <tr>
                <th>kuupäev</th>
                <th>pealkiri</th>
                <th>allikas</th>
                <th>juhtloik</th>
            </tr>
        </thead>
        <tbody>
            {''.join(html_rows)}
        </tbody>
    </table>
    </body>
    </html>
    """

    components.html(html_table, height=600, scrolling=True)



# --- PAREMPOOLNE VEERG (Infooperatsioonide loetelu) ---
# --- PAREMPOOLNE VEERG (Infooperatsioonide loetelu) ---
with parem:
    st.markdown("## 🔦 Olulisemad operatsioonid")

    operatsioonid = {
        "Operation Overload": ["overload"],
        "Operation Matrjoshka": ["matrjoshka", "matrjoška", "matryoshka"],
        "Operation Doppelgänger": ["doppelgänger", "doppelganger"],
        "Operation False Façade (Storm-1516)": ["false façade", "storm-1516", "false facade", "storm 1516"],
        "Operation Portal Kombat": ["portal kombat"],
        "Operation Undercut": ["undercut"],
        "Pravfond": ["pravfond"]
    }

    def set_search(keywords):
        cleaned = [normalize(k) for k in keywords]
        st.session_state.search_override = " OR ".join(cleaned)

    for nimi, märksõnad in operatsioonid.items():
        st.button(
            label=nimi,
            key=nimi,
            on_click=set_search,
            args=(märksõnad,)
        )

# --- SULE ANDMEBAAS ---
conn.close()





