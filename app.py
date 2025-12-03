# app.py
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
st.write("If this UI needs to match specific columns in your CSV, tell me the column names or paste first 10 rows and i'll adapt the app.")

