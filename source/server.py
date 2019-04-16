from flask import Flask
import json
import datetime
import requests
import os
from pymongo import MongoClient
from routing import graph
from routing import osm_handler
from routing import configuration


mongo_client = MongoClient()
db_client = mongo_client['osm']
map_graph = graph.Graph(db_client)
handler = osm_handler.OsmHandler(db_client)
config = configuration.Configuration()

app = Flask(__name__)


@app.route("/api/0.5/fullroute/<float:lat1>,<float:lon1>,<float:lat2>,<float:lon2>")
def route(lat1: float, lon1: float, lat2: float, lon2: float):

    node1 = map_graph.find_nearest([lat1, lon1])
    node2 = map_graph.find_nearest([lat2, lon2])

    path_right = map_graph.astar(node1['_id'], node2['_id'])
    path_right = list(path_right) if path_right else []
    length_right = 0
    for i, node in enumerate(path_right):
        if i == len(path_right) - 1:
            break
        length_right = length_right + map_graph.distance_between(node, path_right[i + 1])
    path_right = map_graph.clarify_path_to_loc(path_right) if path_right else []

    path_left = map_graph.astar(node1['_id'], node2['_id'], nodes_client_for_left=map_graph.db_client.nodes)
    path_left = list(path_left) if path_left else []
    length_left = 0
    for i, node in enumerate(path_left):
        if i == len(path_left) - 1:
            break
        length_left = length_left + map_graph.distance_between(node, path_left[i + 1])
    path_left = map_graph.clarify_path_to_loc(path_left) if path_left else []
    #print('\tleft: ', path_left)

    return json.dumps({
        'from': {'lat': lat1, 'lon': lon1},
        'to': {'lat': lat2, 'lon': lon2},
        'path_right': path_right,
        'distance_right': length_right,
        'path_left': path_left,
        'distance_left': length_left,
    })

@app.route("/api/0.5/route_id/<int:id1>,<int:id2>")
def route_id(id1: int, id2: int):
    path = map_graph.astar(id1, id2)
    path = list(path) if path else []
    return json.dumps(path)

@app.route("/api/0.5/fullroute_id/<int:id1>,<int:id2>")
def fullroute_id(id1: int, id2: int):
    path = list(map_graph.astar(id1, id2))
    path = map_graph.clarify_path_to_loc(path) if path else []
    return json.dumps(path)

@app.route("/api/0.5/create_backup")
def create_backup():
    handler.create_backup(config.get_bounds())
    config.set_backup_info({
        'exist': True,
        'path': '../settings/backup.json',
        'date': datetime.datetime.today().strftime("%d.%m.%Y %H:%M")
    })
    config.save_config()
    return 'Backup created'

@app.route("/api/0.5/load_backup")
def load_backup():
    info = config.get_backup_info()
    if info['exist']:
        bounds = handler.load_backup(info['path'])
        config.set_bounds(bounds)
        config.save_config()
        return 'Backup loaded'
    return "Backup doesn't exist"

@app.route("/api/0.5/load_map/<float:min_lat>,<float:min_lon>,<float:max_lat>,<float:max_lon>")
def load_map(min_lat: float, min_lon: float, max_lat: float, max_lon: float):
    r = requests.get('https://overpass-api.de/api/map?bbox='+str(min_lon)+','+str(min_lat)+','+str(max_lon)+','+str(max_lat), stream=True)
    if r.status_code == 200:
        with open(os.path.join('..', 'settings', 'tmp.osm'), 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
    bounds = handler.parse(open(os.path.join('..', 'settings', 'tmp.osm'), 'r', encoding='utf8'))
    if os.path.isfile(os.path.join('..', 'settings', 'tmp.osm')):
        os.remove(os.path.join('..', 'settings', 'tmp.osm'))
    if bounds not in config.get_bounds():
        config.add_bounds(bounds)
        config.save_config()
        return 'Bounds added'
    return 'Bounds exist'

@app.route("/api/0.5/bounds")
def get_bounds():
    return json.dumps({"bounds": config.get_bounds()})

app.run(host=config.get_ip(), port=config.get_port())

