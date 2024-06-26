import numpy as np
import streamlit as st
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, CustomJS
from bokeh.events import Tap
from bokeh.models import PanTool, WheelZoomTool
from bokeh.palettes import Paired12, Spectral11, Set1, Set3, Category20, Accent
import pandas as pd
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors


st.set_page_config(layout='wide')
spectral = np.hstack([Category20[20] + Set1[9] + Set3[9] + Accent[8] + Paired12 + Spectral11] * 100)


# Read data from CSV into a pandas DataFrame
@st.cache_data
def load_data():
    df = pd.read_csv("cvpr2024_data.csv")
    sentence_embeddings = np.load("cvpr2024_papers_points.npy")
    return df, sentence_embeddings

@st.cache_resource
def get_models():
    sentence_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
    nn_model = NearestNeighbors(n_neighbors=num_results, algorithm='auto', metric='cosine')
    nn_model.fit(sentence_embeddings)
    return sentence_model, nn_model


df, sentence_embeddings = load_data()

st.sidebar.write("Select the number of clusters into which to split the data. Each cluster will have an overarching"
                "theme computed from the list of its paper titles.")
num_clusters = st.sidebar.slider("Number of clusters", min_value=10, max_value=100, step=10)
st.sidebar.write("Then, click on different points on the plot to see what paper they correspond to, read the abstract,"
                 "and go to the CVPR 2024 Open Acess paper page")

num_results = st.sidebar.slider("Number of search results to show", min_value=5, max_value=100, step=1)

themes_file = f"cluster_themes_{num_clusters}"

with open(themes_file, 'rb') as f:
    themes, cluster_indices = pickle.load(f)

themes_list = [themes[i] for i in cluster_indices]

# Streamlit app layout

st.title("CVPR 2024 Papers")

palette = spectral
color = [palette[i] for i in cluster_indices]
size = [5] * len(color)
alpha = [1] * len(color)

query = st.text_input("Natural Language Search")

indices = []
if query:
    sentence_model, nn_model = get_models()
    embedded_query = sentence_model.encode([query])[0]

    distances, indices = nn_model.kneighbors(embedded_query.reshape(1, -1), n_neighbors=num_results)
    indices = indices[0]
    # Highlight search results
    alpha = [0.5] * len(color)
    for i in indices:
        color[i] = "#FFFFFF"
        size[i] = 10
        alpha[i] = 1

# Create a ColumnDataSource
df['Color'] = color
df['Size'] = size
df['Alpha'] = alpha
df['Theme'] = themes_list

source = ColumnDataSource(df)

# Create a Bokeh plot with dark grey background and black points
p = figure(tools="tap,pan,wheel_zoom,reset", tooltips="@Title", width=700, height=700,
           background_fill_color='#333333', border_fill_color='#333333')
p.scatter('X', 'Y', source=source, size="Size", color="Color", alpha="Alpha",
          nonselection_fill_alpha=0.75, selection_fill_color='#FFFFFF')

# Customize grid lines
p.xgrid.grid_line_color = '#222222'
p.ygrid.grid_line_color = '#222222'

# JavaScript code to display text and URL on tap
callback = CustomJS(args=dict(source=source), code="""
    const indices = source.selected.indices;
    if (indices.length > 0) {
        const index = indices[0];
        const data = source.data;
        const theme = data['Theme'][index];
        const title = data['Title'][index];
        const abstract = data['Abstract'][index];
        const url = data['URL'][index];
        document.getElementById('theme').innerText = theme;
        document.getElementById('title').innerText = title;
        document.getElementById('abstract').innerText = abstract;
        document.getElementById('url').href = url;
        document.getElementById('url').innerText = url;
    }
""")

p.js_on_event(Tap, callback)




cols = st.columns(2)

cols[0].bokeh_chart(p, use_container_width=True)

cols[0].markdown("<p>GPT-generated theme:</p>", unsafe_allow_html=True)
cols[0].markdown("<h3>Theme</h3>", unsafe_allow_html=True)
cols[1].markdown("<p id='title'> </p>", unsafe_allow_html=True)
cols[1].markdown("<p id='abstract'>Click on a point to see the details here.</p>", unsafe_allow_html=True)
cols[1].markdown("<a id='url' href='#' target='_blank'></a>", unsafe_allow_html=True)
