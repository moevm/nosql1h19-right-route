from flask import Flask
from routing import graph
from pymongo import MongoClient

file_name = 'vas_ostrov'  # == <db name> after working (without <.osm>!!!)

mongo_client = MongoClient()
db_client = mongo_client[file_name]
map_graph = graph.Graph(db_client)

app = Flask(__name__)


@app.route("/api/0.5/find_path/<int:id1>,<int:id2>")
def hello(id1: int, id2: int):
    path = map_graph.astar(id1, id2)
    path = list(path) if path else []
    return 'path = ' + str(path) + ' km'


app.run()
