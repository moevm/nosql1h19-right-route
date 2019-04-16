import sys
from routing.astar import AStar
from routing.utils import singleton


@singleton
class Graph(AStar):

    def __init__(self, client):
        self.db_client = client
        self.tags = ['motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary',
                     'secondary_link', 'tertiary', 'tertiary_link', 'unclassified', 'residential']
        self.neigh_ways = {}

    def add_neighbor(self, way_id, id_from, id_to, nodes, oneway_flag):
        """
        Добавление соседа узла
        :param way_id: id пути, соединяющего узлы
        :param id_from: id узла-начала
        :param id_to: id узла-конца
        :param nodes: узлы между начальным и конечным узлом
        :param oneway_flag: флаг одностороннего движения
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
                            'way': way_id,
                        }
                    }
            }
        )
        if not oneway_flag:  # если путь не односторонний - добавление обратного
            self.db_client.nodes.update_one(
                {'_id': id_to},
                {
                    '$set':
                        {
                            'neighbors.' + str(id_from): {
                                'distance': length,
                                'way': way_id,
                            }
                        }
                }
            )

    def find_nearest(self, point):
        min = 0
        max = 0.10
        while True:
            nearest = list(self.db_client.nodes.find({
                'loc':
                    {
                        '$near': point,
                        '$minDistance': min,
                        '$maxDistance': max
                    }
            }, {'_id': 1, 'loc': 1}).limit(100))
            for node in nearest:
                if 'neighbors' in node:
                    return node
                tmp = self.db_client.ways.find_one({'tags.highway': {'$in': self.tags}, 'nodes.node_id': node['_id']})
                if tmp:
                    return node
            min = max
            max = max + 0.1

    def distance_between(self, node_id1, node_id2):
        """
        Расстояние между двумя узлами-соседями графа
        :param node_id1: id первого узла
        :param node_id2: id второго узла
        :return:
        """
        dist = self.db_client.nodes.find_one({'_id': node_id1, 'neighbors.' + str(node_id2): {'$exists': 1}},
                                             {'neighbors': 1})
        return dist['neighbors'][str(node_id2)]['distance']

    def heuristic_cost_estimate(self, n1, n2):
        return 0

    def neighbors(self, node):
        """
        Соседи узла
        :param node: id узла
        :return: list(str) - список соседей узла
        """
        node_info = self.db_client.nodes.find_one({'_id': node}, {'tags': 0})
        if 'to_flag' in node_info and node_info['to_flag']:
            if 'neighbors' in node_info:
                return list(node_info['neighbors'].keys())  # если все соседи найдены - передача
            else:
                return []
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

        neighbors = []
        for cur_way in ways:  # проанализировать каждый путь
            oneway_flag = 'oneway' in cur_way['tags']  # если односторонее движение (понадобится позже)
            offset = cur_way['nodes'].index({
                'node_id': node_info['_id'],
                'loc': node_info['loc']
            })  # индекс узла в текущем пути
            tmp = self.search_in_way(cur_way['_id'], node_info, cur_way['nodes'][offset::],
                                     oneway_flag)  # поиск соседнего узла впереди
            if tmp:
                neighbors.append(str(tmp))
            if not oneway_flag:
                tmp = self.search_in_way(cur_way['_id'], node_info, cur_way['nodes'][offset::-1],
                                         oneway_flag)  # поиск соседнего узла сзади
                if tmp:
                    neighbors.append(str(tmp))
        return list(node_info['neighbors'].keys()) + neighbors if 'neighbors' in node_info else neighbors

    def search_in_way(self, way_id, node, nodes, oneway_flag):
        """
        Поиск соседнего узла в пути
        :param way_id: id пути
        :param node: данные об узле, для которого ищется соседний узел
        :param nodes: список узлов дороги от стартового узла
        :param oneway_flag: флаг одностороннего движения
        :return:
        """
        for i, cur_node in enumerate(nodes[1::]):  # начало со следующего от главного узла
            if 'neighbors' in node and str(cur_node['node_id']) in node['neighbors']:
                return None  # если текущий узел уже записан - конец

            if cur_node['node_id'] not in self.neigh_ways:
                self.neigh_ways[cur_node['node_id']] = list(self.db_client.ways.find(
                    {'nodes': cur_node, 'tags.highway': {'$in': self.tags}}))  # удалено '_id': {'$ne': way_id},
            ways = []
            for a in self.neigh_ways[cur_node['node_id']]:  # сохранённые инцидентные пути
                ways.append(a) if a['_id'] is not way_id else None  # без текущего пути
            if len(ways) > 0 or i == len(nodes) - 2:
                # найдена новая вершина - записать соседа и просчитать длину ребра
                self.add_neighbor(way_id, node['_id'], cur_node['node_id'], nodes[:i + 2], oneway_flag)
                return str(cur_node['node_id'])  # если найден сосед - выход
        return None

    def background_search(self):
        """
        Поиск соседей. Предобработка данных в БД.
        :return: -
        """
        import random
        random_way = self.db_client.ways.find({'tags.highway': {'$in': self.tags}}, {'nodes': 1}).skip(
            random.randint(0, self.db_client.ways.count_documents({'tags.highway': {'$in': self.tags}}) - 1)).limit(1)[
            0]
        stack = set()
        stack.add(random_way['nodes'][random.randint(0, len(random_way['nodes']) - 1)]['node_id'])
        count = 0
        while len(stack) > 0:  # and count < 200:
            node_info = self.db_client.nodes.find_one({'_id': stack.pop()})
            if not ('to_flag' in node_info and node_info['to_flag'] is True):
                count = count + 1
                for a in self.find_all_neigh(node_info):
                    stack.add(int(a))
                print(count, node_info['_id'], len(stack))
            else:
                print('>> skip last')
            '''
            if not stack:
                random_way = self.db_client.ways.find({}, {'nodes': 1}).skip(
                    random.randint(0, self.db_client.ways.count_documents({}) - 1)).limit(1)[0]
                new = random_way['nodes'][random.randint(0, len(random_way['nodes']) - 1)]['node_id']
                stack.add(new)
                print('>>> добавил', new)
            '''
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
            if i == len(path) - 1:
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
