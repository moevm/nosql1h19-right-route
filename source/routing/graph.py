import sys
import logging
import random
from routing.astar import AStar
from routing.utils import singleton


@singleton
class Graph(AStar):

    def __init__(self, client):
        self.db_client = client
        self.tags = ['motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary',
                     'secondary_link', 'tertiary', 'tertiary_link', 'unclassified', 'residential']
        self.str_tags = ''
        for tag in self.tags:
            if tag == self.tags[-1]:
                self.str_tags = self.str_tags + tag
            else:
                self.str_tags = self.str_tags + tag + '|'
        self.neigh_ways = {}
        self.traffic_jam = {}

    def add_neighbor(self, way_info, id_from, id_to, nodes):
        """
        Добавление соседа узла
        :param way_info: информация о пути, соединяющего узлы
        :param id_from: id узла-начала
        :param id_to: id узла-конца
        :param nodes: узлы между начальным и конечным узлом
        :return: -
        """
        length = 0
        for i, loc in enumerate(nodes):
            if i == len(nodes) - 1:
                break
            length = length + haversine(nodes[i]['loc'],
                                        nodes[i + 1]['loc'])  # расчёт длины по точкам (на случай криволинейности)
        # хранение информации о соседях в узле
        self.db_client.nodes.update_one(
            {'_id': id_from},
            {
                '$set':
                    {
                        'neighbors.' + str(id_to): {
                            'distance': length,
                            'time': length * 60 / way_info['maxspeed'],
                            'way': way_info['_id']
                        }
                    }
            }
        )
        if not way_info['oneway']:  # если путь не односторонний - добавление обратного
            self.db_client.nodes.update_one(
                {'_id': id_to},
                {
                    '$set':
                        {
                            'neighbors.' + str(id_from): {
                                'distance': length,
                                'time': length/way_info['maxspeed'],
                                'way': way_info['_id']
                            }
                        }
                }
            )

    def find_nearest(self, point):
        import overpy
        import numpy as np
        api = overpy.Overpass()
        dist = 50
        result = overpy.Result()
        try:
            while not result.ways:
                result = api.query(f"""[out:json];way["highway"~"{self.str_tags}"](around:{dist},{point[0]},{point[1]});out;""")
                dist = dist + 50
        except overpy.OverPyException:
            logging.ERROR('Graph.find_nearest: Ошибка OverPy')
            raise ValueError('Сервер перегружен')

        first_way = self.db_client.ways.find_one({"_id": result.ways[0].id}, {"nodes": 1})  # полученные узлов пути
        if not first_way:
            logging.ERROR('Graph.find_nearest: Путь не найден в БД.')
            raise ValueError('Необходимые данные отсутствуют в БД')
        min1 = dict(id=first_way['nodes'][0]['node_id'], loc=first_way['nodes'][0]['loc'], dist=haversine(point, first_way['nodes'][0]['loc']))
        for way in result.ways:
            tmp_way = self.db_client.ways.find_one({"_id": way.id}, {"nodes": 1})     # полученные узлов пути
            if not tmp_way:
                logging.ERROR('Graph.find_nearest: Путь не найден в БД.')
                raise ValueError('Необходимые данные отсутствуют в БД')
            nodes = tmp_way['nodes'] if tmp_way else []
            for node in nodes:
                dist = haversine(point, node['loc'])
                if dist < min1['dist']:
                    min1['id'] = node['node_id']
                    min1['dist'] = dist
        return min1['id']

    def distance_between(self, node_id1, node_id2, dist_flag=True, way_id=None):
        """
        Расстояние между двумя узлами-соседями графа
        :param node_id1: id первого узла
        :param node_id2: id второго узла
        :param dist_flag:
        :return:
        """
        dist = self.db_client.nodes.find_one({'_id': node_id1, 'neighbors.' + str(node_id2): {'$exists': 1}},
                                             {'neighbors': 1})
        if not dist:
            logging.error('Graph.distance_between: Узел не найден в БД.')
            raise ValueError('Необходимые данные отсутствуют в БД')
        if dist_flag:
            return dist['neighbors'][str(node_id2)]['distance']
        else:
            tmp_time = dist['neighbors'][str(node_id2)]['time']
            if way_id not in self.traffic_jam:
                self.traffic_jam[way_id] = random.choice([1,1,1,2,2,2,3,3,3,4,4,5])   # создание автомобильного трафика
            return tmp_time * 1.5 + tmp_time * 9  / (6 - self.traffic_jam[way_id])    # увеличение времени движения между узлами

    def heuristic_cost_estimate(self, n1, n2):
        return 0

    def neighbors(self, node):
        """
        Соседи узла
        :param node: id узла
        :return: list(str) - список соседей узла
        """
        node_info = self.db_client.nodes.find_one({'_id': node}, {'tags': 0})
        if not node_info:
            logging.error('Graph.neighbors: Узел не найден в БД.')
            raise ValueError('Необходимые данные отсутствуют в БД')
        if 'to_flag' in node_info and node_info['to_flag']:
            if 'neighbors' in node_info:
                tmp = {}
                for neigh, info in node_info['neighbors'].items():
                    tmp[str(neigh)] = info['way']
                return tmp # если все соседи найдены - передача
            else:
                return {}
        else:
            neighbors = self.find_all_neigh(node_info)  # поиск всех соседей, если они не найдены
            self.db_client.nodes.update_one({'_id': node}, {'$set': {'to_flag': True}})  # отметка о всех соседях)
            return neighbors

    def find_all_neigh(self, node_info):
        """
        Поиск всех соседей узла
        :param node_info: данные об узле {'_id', 'loc', 'neighbors'}
        :return: list(str) - список всех соседей узла
        """
        if node_info['_id'] in self.neigh_ways:
            ways = self.neigh_ways[node_info['_id']]
        else:
            ways = list(
                self.db_client.ways.find({'tags.highway': {'$in': self.tags}, 'nodes.node_id': node_info['_id']},
                                         {'_id': 1, 'nodes': 1,
                                          'tags': 1}))  # найти все учитываемые пути, содержащие этот узел
            self.neigh_ways[node_info['_id']] = ways

        neighbors = {}
        for cur_way in ways:  # проанализировать каждый путь
            way_info = {
                '_id': cur_way['_id'],
                'oneway': 'oneway' in cur_way['tags'],
                'maxspeed': cur_way['tags']['maxspeed'] if 'maxspeed' in cur_way['tags'] else 60
            }
            offset = cur_way['nodes'].index({
                'node_id': node_info['_id'],
                'loc': node_info['loc']
            })  # индекс узла в текущем пути
            tmp = self.search_in_way(way_info, node_info, cur_way['nodes'][offset::])  # поиск соседнего узла впереди
            if tmp:
                neighbors[tmp[0]] = tmp[1]
            if not way_info['oneway']:
                tmp = self.search_in_way(way_info, node_info, cur_way['nodes'][offset::-1])  # поиск соседнего узла сзади
                if tmp:
                    neighbors[tmp[0]] = tmp[1]

        if 'neighbors' in node_info:
            for neigh, info in node_info['neighbors'].items():
                neighbors[str(neigh)] = info['way']
        return  neighbors

    def search_in_way(self, way_info, node, nodes):
        """
        Поиск соседнего узла в пути
        :param way_info: данные о пути
        :param node: данные об узле, для которого ищется соседний узел
        :param nodes: список узлов дороги от стартового узла
        :return:
        """
        for i, cur_node in enumerate(nodes[1::]):  # начало со следующего от главного узла
            if 'neighbors' in node and str(cur_node['node_id']) in node['neighbors']:
                return None  # если текущий узел уже записан - конец

            if cur_node['node_id'] not in self.neigh_ways:
                self.neigh_ways[cur_node['node_id']] = list(self.db_client.ways.find(
                    {'tags.highway': {'$in': self.tags}, 'nodes': cur_node}))  # удалено '_id': {'$ne': way_id},
            ways = []
            for a in self.neigh_ways[cur_node['node_id']]:  # сохранённые инцидентные пути
                ways.append(a) if a['_id'] is not way_info['_id'] else None  # без текущего пути
            if len(ways) > 0 or (i == len(nodes) - 2):
                # найдена новая вершина - записать соседа и просчитать длину ребра
                self.add_neighbor(way_info, node['_id'], cur_node['node_id'], nodes[:i + 2])
                return [str(cur_node['node_id']), way_info['_id']]  # если найден сосед - выход
        return None

    def background_search(self):
        """
        Поиск соседей. Предобработка данных в БД.
        :return: -
        """
        random_way = self.db_client.ways.find({'tags.highway': {'$in': self.tags}}, {'nodes': 1}).skip(
            random.randint(0, self.db_client.ways.count_documents({'tags.highway': {'$in': self.tags}}) - 1)).limit(1)[
            0]
        stack = set()
        stack.add(random_way['nodes'][random.randint(0, len(random_way['nodes']) - 1)]['node_id'])
        count = 0
        while len(stack) > 0:
            node_info = self.db_client.nodes.find_one({'_id': stack.pop()})
            if not ('to_flag' in node_info and node_info['to_flag'] is True):
                count = count + 1
                for a in list(self.find_all_neigh(node_info).keys()):
                    stack.add(int(a))
                self.db_client.nodes.update({'_id': node_info['_id']}, {'$set': {'to_flag': True}})

    def delete_graph(self):
        """
        Удаление данных о графе из БД
        :return: -
        """
        self.db_client.nodes.update_many({'to_flag': {'$exists': 1}},
                                         {
                                             '$unset':
                                                 {
                                                     'neighbors': "",
                                                     'to_flag': ""
                                                 }
                                         }
                                         )

    def clarify_path_to_loc(self, path):
        """
        Уточнение пути в координатах (добавление промежуточных узлов)
        :param path: путь из перекрестков
        :return: полный путь
        """
        full_path = []
        for i, node in enumerate(path):
            tmp = self.db_client.nodes.find_one({'_id': node})
            if node == path[-1]:
                full_path.append({'lat': tmp['loc'][0], 'lon': tmp['loc'][1]})
                break
            tmp1 = self.db_client.nodes.find_one({'_id': path[i + 1]})
            way_nodes = self.db_client.ways.find_one({'_id': tmp['neighbors'][str(tmp1['_id'])]['way']}, {'nodes': 1})[
                'nodes']
            index = way_nodes.index({'node_id': tmp['_id'], 'loc': tmp['loc']})
            index1 = way_nodes.index({'node_id': tmp1['_id'], 'loc': tmp1['loc']})
            if index < index1:
                nodes = way_nodes[index:index1+1]
            else:
                nodes = way_nodes[index:index1-1:-1]
            for tmp_node in nodes:
                if tmp_node['node_id'] == path[i + 1]:
                    break
                full_path.append({'lat': tmp_node['loc'][0], 'lon': tmp_node['loc'][1]})
        return full_path


def haversine(point1, point2):
    """
    Рассчет расстояния (в км) между двумя географическими точками
    :param point1: координаты 1ой точки
    :param point2: координаты 2ой точки
    :return: double - расстояние между точками
    """
    from math import radians, cos, sin, asin, sqrt
    lat1, lon1 = point1
    lat2, lon2 = point2
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371.0088
    return c * r


if __name__ == '__main__':
    from pymongo import MongoClient

    mongo = MongoClient()
    map_graph = Graph(mongo.osm)
    mongo.close()
