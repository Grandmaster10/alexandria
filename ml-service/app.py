import streamlit as st
import requests

st.set_page_config(page_title="Alexandria", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600&display=swap');

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Newsreader', serif !important;
        font-weight: 500 !important;
        letter-spacing: -0.02em;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Newsreader', serif !important;
    }

    p, span, div, label {
        font-family: 'Inter', sans-serif;
    }

    .stButton button {
        background-color: #5d574f !important;
        border: none !important;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        transition: opacity 0.2s;
    }
    .stButton button p {
        color: #faf9f6 !important; 
        font-weight: 500 !important;
        margin: 0 !important;
    }
    .stButton button:hover {
        opacity: 0.85;
    }

    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #ffffff !important; 
        color: #000000 !important; 
        -webkit-text-fill-color: #000000 !important;
        border: 1px solid #dbdad7 !important;
        border-radius: 6px;
        font-family: 'Inter', sans-serif !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 32px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

API_URL = "http://backend-api:3001"

st.title("Alexandria")
st.markdown("*An AI-Powered catalogue that reads your mood and recommends you books.*")
st.divider()

tab_explore, tab_catalogue, tab_add = st.tabs([
    "AI Recommender", 
    "The Library", 
    "Contribute Here"
])

with tab_explore:
    st.markdown("### Describe your mood, a vibe, or a book you loved")
    
    user_prompt = st.text_area(
        "What are you looking for?", 
        placeholder="e.g., A gritty detective story with a plot twist, or 'I just read Harry Potter and want more magic...'",
        height=100
    )
    
    if st.button("Discover Books", type="primary"):
        if not user_prompt:
            st.warning("Please enter a description to search.")
        else:
            with st.spinner("Translating your mood into 384 dimensions..."):
                try:
                    res = requests.post(f"{API_URL}/books/search/text", json={"query": user_prompt})
                    if res.status_code in [200, 201]:
                        recommendations = res.json()
                        st.success("Analysis Complete.")
                        
                        for i, book in enumerate(recommendations):
                            col_text, col_score = st.columns([4, 1])
                            with col_text:
                                st.subheader(f"{book.get('title')}")
                                st.caption(f"**{book.get('author')}** |  {book.get('type')}")
                                st.write(book.get('description'))
                            with col_score:
                                match_pct = book.get('similarity', 0) * 100
                                st.metric(label="Match", value=f"{match_pct:.1f}%")
                            st.divider()
                    else:
                        st.error("Failed to fetch recommendations. Ensure backend route exists.")
                except Exception as e:
                    st.error(f"API Error: {e}")

with tab_catalogue:
    st.markdown("### Browse the Collection")
    
    if st.button("Refresh Library"):
        with st.spinner("Fetching 1,500 books..."):
            try:
                res = requests.get(f"{API_URL}/books")
                if res.status_code == 200:
                    books = res.json()
                    st.dataframe(
                        books, 
                        column_config={
                            "id": None,          
                            "title": st.column_config.TextColumn("Title", width="large"),
                            "author": st.column_config.TextColumn("Author", width="medium"),
                            "type": st.column_config.TextColumn("Genre", width="small"),
                            "description": st.column_config.TextColumn("Description", width="large")
                        },
                        hide_index=True,
                        use_container_width=True,
                        height=500
                    )
                else:
                    st.error("Could not load library.")
            except Exception as e:
                st.error(f"API Error: {e}")

with tab_add:
    st.markdown("### Curate the Collection")
    st.markdown("Add a new book. The AI will automatically generate its mathematical brainwave.")
    
    with st.form("add_book_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_title = st.text_input("Book Title")
            new_author = st.text_input("Author")
        with col2:
            new_genre = st.selectbox("Genre", ["Fiction", "Sci-Fi", "Fantasy", "Mystery", "Non-Fiction", "Biography", "Other"])

        new_desc = st.text_area("Plot Summary")
        
        submitted = st.form_submit_button("Embed and Save Book")
        
        if submitted:
            if not new_title or not new_author or not new_desc:
                st.warning("Please fill out the Title, Author, and Plot Summary fields before submitting.")
            else:
                with st.spinner("Processing AI Vector..."):
                    payload = {
                        "title": new_title,
                        "author": new_author,
                        "type": new_genre,
                        "description": new_desc
                    }
                    try:
                        res = requests.post(f"{API_URL}/books", json=payload)
                        if res.status_code == 201:
                            st.success(f"'{new_title}' added to the vector database successfully!")
                        else:
                            st.error(f"Failed to add book: {res.text}")
                    except Exception as e:
                        st.error(f"API Error: {e}")