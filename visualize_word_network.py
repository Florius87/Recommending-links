import pandas as pd
import networkx as nx
from pyvis.network import Network

# Load CSV
df = pd.read_csv("internal_link_recommendations.csv")

# Initialize directed graph
G = nx.DiGraph()

# Clean function to strip domain
def clean_url(url):
    return url.replace("https://florisera.com/", "").strip("/")

# Add filtered edges
for _, row in df.iterrows():
    source = clean_url(str(row.iloc[0]))
    target = clean_url(str(row.iloc[1]))
    score = float(row.iloc[2])

    if score >= 0.3:
        G.add_edge(source, target, weight=score)

# Create interactive network
net = Network(height='750px', width='100%', directed=True, notebook=False)
net.from_nx(G)

# Optional: Show only shortened labels
for node in net.nodes:
    node["label"] = node["id"]

net.repulsion(node_distance=120, spring_length=200)
net.show_buttons(filter_=['physics'])

net.write_html("word_network.html")
print("Saved as word_network.html (URLs stripped)")
