import streamlit as st
import pandas as pd
import os
import re
import urllib.parse

st.set_page_config(page_title="Mood-Based Song Recommender", layout="centered")

# ---------- Configuration: put your files here ----------
TELUGU_CSV = "telugu_songs1_dataset.csv"
HINDI_CSV = "hindi_songs_dataset.csv"

# ---------- Utilities ----------
def read_csv_try(path):
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    try:
        return pd.read_csv(path, encoding="utf-8")
    except Exception:
        try:
            return pd.read_csv(path, encoding="latin1")
        except Exception as e:
            raise RuntimeError(f"Failed to read CSV {path}: {e}")

def detect_mood_col(df):
    if df is None or df.empty:
        return None
    candidates = ['mood','moods','feeling','feels','song_mood','emotion','sentiment']
    cols_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in cols_map:
            return cols_map[cand]
    for low, orig in cols_map.items():
        if 'mood' in low or 'feel' in low or 'sent' in low or 'emotion' in low:
            return orig
    return None

def detect_link_col(df):
    if df is None or df.empty:
        return None
    candidates = ['youtube_link','youtube','link','url','video_url']
    cols_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in cols_map:
            return cols_map[cand]
    for low, orig in cols_map.items():
        if 'youtube' in low or 'link' in low or 'url' in low:
            return orig
    return None

def normalize_mood_series(df, mood_col):
    if mood_col is None:
        return pd.Series([''] * len(df))
    return df[mood_col].astype(str).str.strip().str.lower().fillna('')

def is_youtube_id(s):
    return bool(re.fullmatch(r'[A-Za-z0-9_-]{11}', s or ''))

def fix_telugu_link(val):
    if pd.isna(val):
        return ''
    s = str(val).strip()
    if not s:
        return ''
    if re.match(r'^https?://', s, flags=re.I):
        return s
    if is_youtube_id(s):
        return f'https://youtu.be/{s}'
    if s.startswith('www.'):
        return 'https://' + s
    if 'youtube' in s or 'youtu.be' in s:
        return 'https://' + s
    if '.' in s and ' ' not in s:
        return 'https://' + s
    return ''

def make_youtube_search_link(title, artist=None, movie=None):
    parts = []
    if title:
        parts.append(str(title))
    if artist:
        parts.append(str(artist))
    if movie:
        parts.append(str(movie))
    q = " ".join(parts).strip()
    if not q:
        return ''
    return 'https://www.youtube.com/results?search_query=' + urllib.parse.quote_plus(q)

def first_col_like(df, possibilities):
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    lowmap = {c.lower(): c for c in cols}
    for p in possibilities:
        if p.lower() in lowmap:
            return lowmap[p.lower()]
    for c in cols:
        if 'title' in c.lower() or 'song' in c.lower() or 'name' in c.lower():
            return c
    return cols[0] if cols else None

def prepare_dataset(df, dataset_name):
    if df is None or df.empty:
        return pd.DataFrame(columns=["Title","Artist","Movie","Mood","mood_norm","Link","Dataset"])
    df = df.copy()
    mood_col = detect_mood_col(df)
    if mood_col is None:
        raise RuntimeError(f"Could not detect mood column in dataset '{dataset_name}'")
    df["mood_norm"] = normalize_mood_series(df, mood_col)
    title_col = first_col_like(df, ['song_name','title','song','track','name'])
    artist_col = None
    for c in df.columns:
        if 'artist' in c.lower() or 'singer' in c.lower():
            artist_col = c
            break
    movie_col = None
    for c in df.columns:
        if any(x in c.lower() for x in ("movie","film","album")):
            movie_col = c
            break
    link_col = detect_link_col(df)
    if link_col is None:
        df["auto_link"] = df.apply(lambda r: make_youtube_search_link(r.get(title_col,""), r.get(artist_col,"") if artist_col else "", r.get(movie_col,"") if movie_col else ""), axis=1)
        link_col = "auto_link"
    else:
        df[link_col] = df[link_col].astype(str).apply(fix_telugu_link)
    idx = df.index
    title_s = df[title_col].astype(str) if title_col in df.columns else pd.Series("", index=idx)
    artist_s = df[artist_col].astype(str) if artist_col and artist_col in df.columns else pd.Series("", index=idx)
    movie_s = df[movie_col].astype(str) if movie_col and movie_col in df.columns else pd.Series("", index=idx)
    mood_s = df[mood_col].astype(str) if mood_col in df.columns else pd.Series("", index=idx)
    mood_norm_s = df["mood_norm"]
    link_s = df[link_col].astype(str) if link_col in df.columns else pd.Series("", index=idx)
    clean = pd.DataFrame({
        "Title": title_s.values,
        "Artist": artist_s.values,
        "Movie": movie_s.values,
        "Mood": mood_s.values,
        "mood_norm": mood_norm_s.values,
        "Link": link_s.values,
        "Dataset": [dataset_name] * len(df)
    })
    return clean

# ---------- Load CSVs at startup ----------
tel_df = pd.DataFrame()
hin_df = pd.DataFrame()
tel_loaded = False
hin_loaded = False

if os.path.exists(TELUGU_CSV):
    try:
        tel_df = read_csv_try(TELUGU_CSV)
        tel_loaded = True
    except Exception as e:
        st.warning(f"Could not load Telugu CSV: {e}")

if os.path.exists(HINDI_CSV):
    try:
        hin_df = read_csv_try(HINDI_CSV)
        hin_loaded = True
    except Exception as e:
        st.warning(f"Could not load Hindi CSV: {e}")

telugu_clean = prepare_dataset(tel_df, "Telugu") if tel_loaded else pd.DataFrame()
hindi_clean = prepare_dataset(hin_df, "Hindi") if hin_loaded else pd.DataFrame()

combined = pd.concat([telugu_clean, hindi_clean], ignore_index=True) if (not telugu_clean.empty or not hindi_clean.empty) else pd.DataFrame(columns=telugu_clean.columns if not telugu_clean.empty else ["Title","Artist","Movie","Mood","mood_norm","Link","Dataset"])
if not combined.empty:
    combined = combined.drop_duplicates(subset=["Title"], keep="first").reset_index(drop=True)

all_moods = sorted([m for m in combined["mood_norm"].unique() if str(m).strip()]) if not combined.empty else []

# ---------- Streamlit UI ----------
st.title("🎧 Mood-Based Song Recommender")
st.write("Select a mood (detected from your CSVs) or type one. Telugu songs are prioritized in results.")

with st.sidebar:
    st.header("Filters")
    if all_moods:
        mood_choice = st.selectbox("Choose mood (detected)", ["-- Choose --"] + all_moods)
        mood_text = st.text_input("Or type mood (fallback)", "")
    else:
        st.write("No mood column detected in CSVs.")
        mood_choice = "-- Choose --"
        mood_text = st.text_input("Type mood", "")
    source_choice = st.multiselect("Source (language)", ["All", "Telugu", "Hindi"], default=["All"])

sel_mood = (mood_text.strip().lower()) if mood_text.strip() else (mood_choice if mood_choice and mood_choice != "-- Choose --" else "")

if combined.empty:
    st.warning("No data loaded. Make sure the CSV files are present in the repository root with the correct filenames.")
    st.stop()

st.write(f"Detected moods (sample): {', '.join(all_moods[:30]) if all_moods else '—'}")
st.write(f"Matching songs for mood: *{sel_mood or '—'}*")

if sel_mood:
    tel_matches = combined[(combined["mood_norm"] == sel_mood) & (combined["Dataset"] == "Telugu")]
    hin_matches = combined[(combined["mood_norm"] == sel_mood) & (combined["Dataset"] == "Hindi")]
    final = pd.concat([tel_matches, hin_matches], ignore_index=True)
else:
    final = combined.copy()

# apply source filter — make sure we reference source_choice (same name as above)
if source_choice and "All" not in source_choice:
    final = final[final["Dataset"].isin(source_choice)]

final = final.drop_duplicates(subset=["Title"], keep="first").reset_index(drop=True)
st.markdown(f"{len(final)}** songs found")

if final.empty:
    st.info("No songs match your filters. Try a different mood or allow both sources.")
else:
    n = st.slider("Number of recommendations to show", 1, min(100, max(1, len(final))), min(10, len(final)))
    display_df = final.head(n).copy()
    def ensure_link(row):
        link = row.get("Link","") or ""
        if row.get("Dataset","") == "Telugu" and not link:
            return make_youtube_search_link(row.get("Title",""), row.get("Artist",""), row.get("Movie",""))
        return link
    display_df["Link"] = display_df.apply(ensure_link, axis=1)
    display_df.index = range(1, len(display_df)+1)
    show_cols = ["Title","Movie","Mood","Dataset","Link"]
    st.dataframe(display_df[show_cols], use_container_width=True)
    st.markdown("---")
    st.subheader("Open a song")
    for i, row in display_df.iterrows():
        title = row["Title"]
        artist = row.get("Artist","")
        url = row.get("Link","")
        if url:
            st.markdown(f"{i}. {title}** — {artist} — [{url}]({url})")
        else:
            st.markdown(f"{i}. {title}** — {artist} — (no link)")

st.markdown("---")
st.caption("If the UI doesn't match your CSV columns, tell me the column names or paste first 10 rows and I'll adapt the app.")
