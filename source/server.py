import datetime
import json
import os
import requests
import random
import threading
import logging
from flask import Flask
from flask import request
from pymongo import MongoClient
from routing import configuration
from routing import graph
from routing import osm_handler
from routing.utils import bring_closer

mongo_client = MongoClient()
db_client = mongo_client['osm']
map_graph = graph.Graph(db_client)
handler = osm_handler.OsmHandler(db_client)
config = configuration.Configuration()

logging.basicConfig(filename="server.log", level=logging.INFO)

app = Flask(__name__)

import string
import random
def id_generator(size=10, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for _ in range(size))

def process_back_search(id):
	map_graph.background_search()
	info = config.get_tmp_by_key(id)
	info['data'] = {'isEnd': True}
	config.set_tmp_by_key(id, info)
	logging.info('Server. Back_search has finished.')


def process_backup_create(id):
	handler.create_backup(config.get_bounds())
	config.set_backup_info({
		'exist': True,
		'path': '../settings/backup.json',
		'date': datetime.datetime.today().strftime("%d.%m.%Y %H:%M")
	})
	config.save_config()
	info = config.get_tmp_by_key(id)
	info['data'] = config.get_backup_info()
	config.set_tmp_by_key(id, info)
	logging.info('Server. Backup_create has finished.')

def process_backup_load(path, id):
	bounds = handler.load_backup(path)
	config.set_bounds(bounds)
	config.save_config()
	info = config.get_tmp_by_key(id)
	info['data'] = config.get_backup_info()
	config.set_tmp_by_key(id, info)
	logging.info('Server. Backup_load has finished.')

def process_map(str_req, id):
	r = requests.get(str_req, stream=True)
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
		info = config.get_tmp_by_key(id)
		info['data'] = {'bounds': bounds}
		config.set_tmp_by_key(id, info)
		logging.info('Server. Process_map has finished.')
	else:
		logging.error('Server.Process_map: Ошибка скачивания карты.')


@app.route("/api/0.5/fullroute")
# /api/0.5/fullroute?lat1=1.1&lon1=1.2&lat2=2.1&lon2=2.2
def route():
	try:
		lat1 = float(request.args.get('lat1'))
		lon1 = float(request.args.get('lon1'))
		lat2 = float(request.args.get('lat2'))
		lon2 = float(request.args.get('lon2'))
	except:
		logging.error("Server.fullroute: Неверные аргументы запроса")
		return json.dumps(
			{
				'error': True,
				'data': {},
				'msg': "Error in args"
			})

	try:
		node1 = map_graph.find_nearest([lat1, lon1])
		node2 = map_graph.find_nearest([lat2, lon2])
		logging.info(f'Routing {node1}, {node2}')

		right = map_graph.astar(node1, node2)
		path_right = []
		time_right = 0
		length_right = 0
		if right:
			path_right = right['path']
			time_right = right['dist']
		for i, node in enumerate(path_right):
			if i == len(path_right) - 1:
				break
			length_right = length_right + map_graph.distance_between(node, path_right[i + 1])
		path_right = map_graph.clarify_path_to_loc(path_right) if path_right else []
		if path_right:
			if len(path_right) > 1:
				start = bring_closer({'loc': [lat1, lon1], 'nodes': [[a['lat'], a['lon']] for a in path_right[0:2]]})
				middle = path_right[1:len(path_right) - 1]
				end = bring_closer({'loc': [lat2, lon2], 'nodes': [[a['lat'], a['lon']] for a in
															   path_right[len(path_right) - 1:len(path_right) - 3:-1]]})
				end.reverse()
			else:
				start = {'lat': lat1, 'lon': lon1}
				middle = path_right
				end = {'lat': lat2, 'lon': lon2}
			path_right = start + middle + end

		left = map_graph.astar(node1, node2, nodes_client_for_left=map_graph.db_client.nodes)
		path_left = []
		time_left = 0
		length_left = 0
		if left:
			path_left = left['path']
			time_left = left['dist']
		for i, node in enumerate(path_left):
			if i == len(path_left) - 1:
				break
			length_left = length_left + map_graph.distance_between(node, path_left[i + 1])
		path_left = map_graph.clarify_path_to_loc(path_left) if path_left else []
		if path_left:
			if len(path_left) > 1:
				start = bring_closer({'loc': [lat1, lon1], 'nodes': [[a['lat'], a['lon']] for a in path_left[0:2]]})
				middle = path_left[1:len(path_left) - 1]
				end = bring_closer({'loc': [lat2, lon2], 'nodes': [[a['lat'], a['lon']] for a in
															   path_left[len(path_left) - 1:len(path_left) - 3:-1]]})
				end.reverse()
			else:
				start = {'lat': lat1, 'lon': lon1}
				middle = path_left
				end = {'lat': lat2, 'lon': lon2}

			path_left = start + middle + end
	except ValueError as e:
		return json.dumps({'error': True, 'data': {}, 'msg': str(e)})

	logging.info(f"""Send this:
		{{
			'error': False,
			'data': {{
				'from': {{'lat': {lat1}, 'lon': {lon1}}},
				'to': {{'lat': {lat2}, 'lon': {lon2}}},
				'path_right': {path_right},
				'distance_right': {length_right},
				'time_right': {time_right},
				'path_left':{path_left},
				'distance_left': {length_left},
				'time_left': {time_left}
			}},
			'msg': "Full routing"
		}}
	""")
	return json.dumps(
		{
			'error': False,
			'data': {
				'from': {'lat': lat1, 'lon': lon1},
				'to': {'lat': lat2, 'lon': lon2},
				'path_right': path_right,
				'distance_right': length_right,
				'time_right': time_right,
				'path_left': path_left,
				'distance_left': length_left,
				'time_left': time_left
			},
			'msg': "Full routing"
		})


@app.route("/api/0.5/route_id")
# /api/0.5/route_id?id1=11&id2=22
def route_id():
	try:
		id1 = int(request.args.get('id1'))
		id2 = int(request.args.get('id2'))
	except:
		return json.dumps({'error': True, 'data': {}, 'msg': "Error in args"})
	try:
		path = map_graph.astar(id1, id2)
	except ValueError as e:
		return json.dumps({'error': True, 'data': {}, 'msg': str(e)})
	path = list(path) if path else []
	return json.dumps(
		{
			'error': False,
			'data': {'path': path},
			'msg': "Routing by id"
		})


@app.route("/api/0.5/fullroute_id")
# /api/0.5/fullroute_id?id1=11&id2=22
def fullroute_id():
	try:
		id1 = int(request.args.get('id1'))
		id2 = int(request.args.get('id2'))
	except:
		logging.error("Server.fullroute_id: Неверные аргументы запроса")
		return json.dumps({'error': True, 'data': {}, 'msg': "Error in args"})
	try:
		path = map_graph.astar(id1, id2)
	except ValueError as e:
		return json.dumps({'error': True, 'data': {}, 'msg': str(e)})

	path = map_graph.clarify_path_to_loc(path) if path else []
	return json.dumps(
		{
			'error': False,
			'data': {'path': path},
			'msg': "Full routing by id"
		})


@app.route("/api/0.5/create_backup")
def create_backup():
	id = id_generator()
	thread = threading.Thread(target=process_backup_create, args=(id,))
	config.add_tmp(id, {'thread': thread})
	thread.start()
	logging.info("Server.create_backup: Создание backup'a...")
	return json.dumps(
		{
			'error': False,
			'data': {'id': id},
			'msg': "Backup is starting"
		})


@app.route("/api/0.5/load_backup")
def load_backup():
	info = config.get_backup_info()
	if info['exist']:
		id = id_generator()
		thread = threading.Thread(target=process_backup_load, args=(info['path'],id))
		config.add_tmp(id, {'thread': thread})
		thread.start()
		logging.info("Server.load_backup: Загрузка backup'a...")
		return json.dumps(
			{
				'error': False,
				'data': {'id': id},
				'msg': "Backup is loading"
			})
	logging.info('Server.load_backup: Backup отсутствует')
	return json.dumps(
		{
			'error': True,
			'data': {},
			'msg': "Backup doesn't exist"
		})


@app.route("/api/0.5/load_map")
# /api/0.5/load_map?min_lat=1.1&min_lon=1.2&max_lat=2.1&max_lon=2.2
def load_map():
	try:
		min_lat = float(request.args.get('min_lat'))
		min_lon = float(request.args.get('min_lon'))
		max_lat = float(request.args.get('max_lat'))
		max_lon = float(request.args.get('max_lon'))
	except:
		logging.error("Server.load_map: Неверные аргументы запроса")
		return json.dumps({'error': True, 'data': {}, 'msg': "Error in args"})
	str_req = 'https://overpass-api.de/api/map?bbox=' + str(min_lon) + ',' + str(min_lat) + ',' + str(max_lon) + ',' + str(max_lat)
	id = id_generator()
	thread = threading.Thread(target=process_map, args=(str_req,id))
	config.add_tmp(id, {'thread': thread})
	thread.start()
	logging.info('Server.load_map: Скачивание карты началось.')
	return json.dumps(
		{
			'error': False,
			'data': {'id': id},
			'msg': "Downloading has been started"
		})


@app.route("/api/0.5/bounds")
def get_bounds():
	logging.info(f"""Send this:
			{{
				'error': False,
				'data': {{'bounds': {config.get_bounds()}}},
				'msg': "Map's bounds"
			}}
	""")
	return json.dumps(
		{
			'error': False,
			'data': {'bounds': config.get_bounds()},
			'msg': "Map's bounds"
		})


@app.route("/api/0.5/back_search")
def back_search():
	logging.warning('Server. Фоновый поиск запущен.')
	id = id_generator()
	thread = threading.Thread(target=process_back_search, args=(id,))
	config.add_tmp(id, {'thread': thread})
	thread.start()
	return json.dumps({
		'error': False,
		'data': {'id': id},
		'msg': "Searching has been started"
	})


@app.route("/api/0.5/check")
# /api/0.5/check?id=string
def check():
	try:
		id = request.args.get('id')
	except:
		logging.error("Server.check: Неверные аргументы запроса")
		return json.dumps({'error': True, 'data': {}, 'msg': "Error in args" })
	info = config.get_tmp_by_key(id)
	if not info:
		# если поток не отслеживается
		return json.dumps({
			'error': True,
			'data': {'run': False, 'data': {}},
			'msg': "Thread is not monitored."
		})
	if info['thread'].isAlive():
		# если поток ещё запущен
		return json.dumps({
			'error': False,
			'data': {'run': True, 'data': {}},
			'msg': "Thread is still running"
		})
	else:
		if 'data' in info:
			# поток завершился, данные существуют
			config.del_tmp(id)
			return json.dumps({
				'error': False,
				'data': {'run': False, 'data': info['data']},
				'msg': "Thread has finished"
			})
		else:
			# поток завершился, данные не существуют
			config.del_tmp(id)
			return json.dumps({
				'error': True,
				'data': {'run': False, 'data': {}},
				'msg': "Smth was wrong"
			})


@app.route("/api/0.5/delete_graph")
def delete_graph():
	logging.warning('Server. Удаление графа из БД.')
	map_graph.delete_graph()
	return json.dumps({
		'error': False,
		'data': {},
		'msg': "Graph has been deleted"
	})


@app.route("/api/0.5/drop")
def drop():
	logging.warning('Server. Удаление БД.')
	db_client.nodes.drop()
	db_client.ways.drop()
	handler.create_indexes()
	config.set_bounds([])
	return json.dumps({
			'error': False,
			'data': {},
			'msg': "DB has been dropped"
		})


app.run(host=config.get_ip(), port=config.get_port(), debug=True)
