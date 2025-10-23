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

st.markdown("""
    <style>
    /* Vasakjoondus ja täislaius nuppudele */
    button[kind="secondary"] {
        width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
    }

    /* Ka tekstinupu sees oleva divi joondus */
    button[kind="secondary"] div[data-testid="stMarkdownContainer"] {
        text-align: left !important;
        justify-content: flex-start !important;
    }

    /* Väiksem fondi suurus pealkirjale väiksel ekraanil */
    @media screen and (max-width: 768px) {
        .operatsioonid-pealkiri {
            font-size: 1rem !important;
        }
    }
    </style>
""", unsafe_allow_html=True)


# --- TIITEL ---
st.markdown(
    """
    <h1 style='text-align: center; color: #2C3E50;'>
        <a href="" style="text-decoration: none; color: inherit;">
            Infomõjutuse kajastused
        </a>
    </h1>
    """,
    unsafe_allow_html=True
)


# --- ANDMEBAAS ---
conn = sqlite3.connect("infomojutus.db")
df = pd.read_sql_query("SELECT * FROM artiklid", conn)
df["kuupäev"] = pd.to_datetime(df["kuupäev"], format="%d.%m.%Y", errors="coerce")
df = df.sort_values(by="kuupäev", ascending=False)  # ← see lisab vaikimisi järjestuse uuemast vanimani


# --- KOLM JAOTUST ---
vasak, keskmine, parem = st.columns([1, 3, 1])

# --- VASAKPOOLNE VEERG (Filtrid + Statistika) ---
with vasak:
    st.markdown("## Otsing")
    # Kui klõpsati teemanuppu, kasuta seda vaikimisi valikuna
    if "teema_valik" in st.session_state:
        vaikimisi_teema_valik = st.session_state["teema_valik"]
    else:
        vaikimisi_teema_valik = []

    teema_valik = st.multiselect("Vali teema:", sorted(df["teema"].dropna().unique()), default=vaikimisi_teema_valik)

    min_kuup = df["kuupäev"].min()
    max_kuup = df["kuupäev"].max()
    kuup_range = st.date_input("📆 Vali kuupäevavahemik:", [min_kuup, max_kuup])
    raw_otsing = st.text_input("🔎 Otsi sõna järgi:", placeholder="nt. Ukraina, NATO, propaganda...")
    otsing = raw_otsing if st.session_state.search_override is None else st.session_state.search_override
    st.session_state.search_override = None


    st.markdown("---")
    st.markdown(f"**Kirjeid kokku:** `{len(df)}`")
    st.markdown(f"**Erinevaid teemasid:** `{df['teema'].nunique()}`")

    viimati_uuendatud = df["kuupäev"].max()
    st.markdown(f"**Viimati uuendatud:** `{viimati_uuendatud.strftime('%d.%m.%Y')}`")

    st.markdown("### Teemade jaotus:")
    teema_arvud = df["teema"].value_counts()

    def set_teema_filter(valitud_teema):
        st.session_state["teema_valik"] = [valitud_teema]

    for teema, arv in teema_arvud.items():
        if arv >= 5:
            st.button(f"{teema} ({arv})", key=f"teema_{teema}", on_click=set_teema_filter, args=(teema,))

    st.markdown("---")
    if st.button("🔄 Tühjenda cache ja käivita uuesti"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

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
    otsing_clean = (
        otsing.replace('"', '')
              .replace("'", "")
              .replace("“", "")
              .replace("”", "")
    ).strip()

    # Kontrollime, kas kasutatakse OR või AND
    if " OR " in otsing_clean:
        raw_keywords = otsing_clean.split(" OR ")
        keywords = [normalize(k.strip()) for k in raw_keywords]

        def contains_keywords(row):
            row_text = normalize(str(row.values))
            return any(k in row_text for k in keywords)

    elif " AND " in otsing_clean:
        raw_keywords = otsing_clean.split(" AND ")
        keywords = [normalize(k.strip()) for k in raw_keywords]

        def contains_keywords(row):
            row_text = normalize(str(row.values))
            return all(k in row_text for k in keywords)

    else:
        keywords = [normalize(otsing_clean)]

        def contains_keywords(row):
            row_text = normalize(str(row.values))
            return all(k in row_text for k in keywords)

    filtered_df = filtered_df[filtered_df.apply(contains_keywords, axis=1)]


filtered_df["kuupäev"] = filtered_df["kuupäev"].dt.strftime("%d.%m.%Y")

# --- KESKMINE VEERG (Artiklid) ---
with keskmine:
    st.markdown("### Artiklid")

    # Tagame, et vajalikud veerud on olemas
    for col in ["kuupäev", "pealkiri", "allikas", "juhtloik"]:
        if col not in filtered_df.columns:
            filtered_df[col] = ""

    # Kuvame klikitava pealkirja (kas st.markdown() või tavaline tekst)
    def make_clickable(row):
        return f"[{row.pealkiri}]({row.link})" if pd.notna(row.link) else row.pealkiri

    filtered_df["pealkiri"] = filtered_df.apply(make_clickable, axis=1)

    # Ainult vajalikud veerud
    filtered_df_display = filtered_df[["kuupäev", "pealkiri", "allikas", "juhtloik"]].copy()

    # Kuvame artiklid tabelina
    for i, row in filtered_df_display.iterrows():
        st.markdown(f"**{row['kuupäev']}**  \n{row['pealkiri']}  \n*{row['allikas']}*  \n{row['juhtloik']}")
        st.markdown("---")


# --- PAREMPOOLNE VEERG (Infooperatsioonide loetelu) ---
# --- PAREMPOOLNE VEERG (Infooperatsioonide loetelu) ---
with parem:
    st.markdown(
    """
    <style>
    @media screen and (max-width: 768px) {
        .operatsioonid-pealkiri {
            font-size: 16px !important;
        }
    }
    </style>
    <h2 class="operatsioonid-pealkiri" style="font-size: 20px;">Olulisemad operatsioonid</h2>
    """,
    unsafe_allow_html=True
)

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





