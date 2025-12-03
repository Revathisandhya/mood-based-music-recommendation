# app.py
import streamlit as st
import pandas as pd
import random
from pathlib import Path

st.set_page_config(page_title="Mood-based Music Recommendation", layout="centered")

st.title("Mood-based Music Recommendation 🎧")
st.write("A simple web UI for your mood-based recommender")

# load datasets (adjust filenames if your csv names are different)
DATA_DIR = Path(".")
files = {
    "hindi": DATA_DIR / "hindi_songs_dataset.csv",
    "telugu": DATA_DIR / "telugu_songs1_dataset.csv"
}

# load safely
dfs = []
for name, path in files.items():
    if path.exists():
        try:
            df = pd.read_csv(path)
            df["__source"] = name
            dfs.append(df)
        except Exception as e:
            st.error(f"Error reading {path.name}: {e}")
if not dfs:
    st.error("No dataset files found. Put your CSVs in repo root or update the filenames in app.py")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

st.sidebar.header("Filters")
# try to find a mood column
mood_col = None
for c in df.columns:
    if c.lower() in ("mood", "moods", "emotion", "feel"):
        mood_col = c
        break

if mood_col:
    moods = sorted(df[mood_col].dropna().astype(str).unique())
    chosen_mood = st.sidebar.selectbox("Choose mood", ["All"] + moods)
else:
    st.sidebar.write("No mood column detected in CSVs.")
    chosen_mood = st.sidebar.text_input("Enter mood (free text)", "")

# optional language/source filter
sources = sorted(df["__source"].unique())
chosen_source = st.sidebar.multiselect("Source (language)", ["All"] + sources, default=["All"])

# Filtering
filtered = df.copy()
if chosen_mood and chosen_mood != "All":
    if mood_col:
        filtered = filtered[filtered[mood_col].astype(str).str.lower() == chosen_mood.lower()]
    else:
        # fallback: try to find mood token in a 'Tags' or 'genre' column if present
        fallback_cols = [c for c in df.columns if c.lower() in ("tags", "genre", "description")]
        if fallback_cols:
            mask = False
            for c in fallback_cols:
                mask = mask | filtered[c].astype(str).str.contains(chosen_mood, case=False, na=False)
            filtered = filtered[mask]
        else:
            # if nothing matches, show empty
            filtered = filtered.iloc[0:0]

if "All" not in chosen_source:
    filtered = filtered[filtered["__source"].isin(chosen_source)]

st.write(f"Found *{len(filtered)}* matching songs")

# simple recommend: show random sample of matched rows
if len(filtered) > 0:
    n = st.slider("Number of recommendations", 1, 20, 5)
    sample = filtered.sample(min(n, len(filtered)), random_state=42)
    # display relevant columns
    display_cols = [c for c in ("song", "title", "artist", "mood", mood_col) if c in sample.columns]
    if not display_cols:
        # just show the first 4 columns
        display_cols = list(sample.columns[:4])
    st.table(sample[display_cols].reset_index(drop=True))
else:
    st.info("No songs match your filters. Try different mood or source.")

st.markdown("---")
st.write("If this UI needs to match specific columns in your CSV, tell me which columns exist (or paste first 10 lines) and I will adapt the app.")
