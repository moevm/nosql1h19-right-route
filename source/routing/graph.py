import sys
from routing.astar import AStar
from routing.utils import singleton


@singleton
class Graph(AStar):

    def __init__(self, client):
        self.db_client = client
        self.tags = ['motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary',
                     'secondary_link', 'tertiary', 'tertiary_link', 'unclassified', 'residential']
        self.lastStatString = ""
        self.stat_ways = 0
        self.stat_nodes = 0

    def add_neighbor(self, way_id, id_from, id_to, locs, oneway_flag):
        """
        Добавление соседа узла
        :param way_id: id пути, соединяющего узлы
        :param id_from: id узла, из которого идём
        :param id_to: id узла, в который идём
        :param locs: координаты узлов между начальным и конечным узлом
        :param oneway_flag: флаг одностороннего движения
        :return: -
        """
        self.stat_nodes = self.stat_nodes + 1
        length = 0
        for i, loc in enumerate(locs):
            if i == len(locs) - 1:
                break
            length = length + haversine(loc, locs[i + 1])  # расчёт длины по точкам (на случай криволинейности)
        # хранение информации о соседях в узле
        self.db_client.nodes.update_one(
            {'_id': id_from},
            {
                '$push':
                    {
                        'neighbors': {
                            'to': id_to,
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
                    '$push':
                        {
                            'neighbors': {
                                'to': id_from,
                                'distance': length,
                                'way': way_id,
                            }
                        }
                }
            )

    def distance_between(self, node_id1, node_id2):
        """
        Расстояние между двумя узлами-соседями графа
        :param node_id1: id первого узла
        :param node_id2: id второго узла
        :return:
        """
        dist = self.db_client.nodes.find_one({'_id': node_id1, 'neighbors.to': node_id2}, {'neighbors': 1})
        # fixme исключение - между двумя точками есть больше 1 пути (например, круговое)
        #  пока берём первый
        for neigh in dist['neighbors']:
            if neigh['to'] == node_id2:
                return neigh['distance']

    def heuristic_cost_estimate(self, n1, n2):
        return 0

    def neighbors(self, node):
        """
        Соседи узла
        :param node: id узла
        :return: list(ids соседей)
        """
        node_info = self.db_client.nodes.find_one({'_id': node}, {'_id': 1, 'to_flag': 1, 'neighbors': 1})
        if 'to_flag' in node_info and node_info['to_flag']:  # вообще поле добавляется только когда флаг True
            if 'neighbors' in node_info:
                return list(node_info['neighbors'].keys())
            else:
                return []
        else:
            neighbors = self.find_all_neigh(node_info)
            self.db_client.nodes.update_one({'_id': node}, {'$set': {'to_flag': True}})
            return neighbors

    def find_all_neigh(self, node_info):
        # не учитывать соседей, уже записанных в узел
        node_id = node_info['_id']
        prev_ways = [a['way'] for a in node_info['neighbors']] if 'neighbors' in node_info else []
        prev_neighbors = [a['to'] for a in node_info['neighbors']] if 'neighbors' in node_info else []
        # prev_dist = node_info['distances'] if 'distances' in node_info else []
        # найти все учитываемые пути, содержащие этот узел
        ways = list(self.db_client.ways.find({'tags.highway': {'$in': self.tags}, 'nodes.node_id': node_id},
                                        {'_id': 1, 'nodes': 1, 'loc': 1, 'tags': 1}))
        neighbors = []
        for cur_way in ways:  # проанализировать каждый путь
            oneway_flag = 'oneway' in cur_way['tags']  # если односторонее движение (понадобится позже)
            offset = -1
            for i, node in enumerate(cur_way['nodes']):
                if node['node_id'] == node_id:
                    offset = i
            for i in range(offset + 1, len(cur_way['nodes'])):  # проанализировать спереди
                # не учитывать узлы, что уже указаны - fixme а если движение круговое?
                if cur_way['_id'] in prev_ways and cur_way['nodes'][i]['node_id'] in prev_neighbors:
                    break
                count_ways = self.db_client.ways.count_documents(
                    {'_id': {'$ne': cur_way['_id']}, 'nodes.to': cur_way['nodes'][i]['node_id'], 'tags.highway': {'$in': self.tags}})
                # теги для того, чтобы не учитывать узлы-пересечения c ненужными путями
                if count_ways > 0 or i == len(cur_way['nodes']) - 1:
                    # найдена новая вершина - записать соседа и просчитать длину ребра
                    self.add_neighbor(cur_way['_id'], node_id, cur_way['nodes'][i]['node_id'], [a['loc'] for a in cur_way['nodes'][offset:i + 1]], oneway_flag)
                    neighbors.append(cur_way['nodes'][i]['node_id'])
                    break
            if not oneway_flag:
                for i in range(offset - 1, -1, -1):  # проанализировать сзади
                    # не учитывать узлы, что уже указаны - fixme а если движение круговое?
                    if cur_way['_id'] in prev_ways and cur_way['nodes'][i]['node_id'] in prev_neighbors:
                        break
                    count_ways = self.db_client.ways.count_documents(
                        {'_id': {'$ne': cur_way['_id']}, 'nodes': cur_way['nodes'][i]['node_id'], 'tags.highway': {'$in': self.tags}})
                    # теги для того, чтобы не учитывать узлы-пересечения c ненужными путями
                    if count_ways > 0 or i == 0:
                        # найдена новая вершина - записать соседа и просчитать длину ребра
                        self.add_neighbor(cur_way['_id'], node_id, cur_way['nodes'][i]['node_id'], [a['loc'] for a in cur_way['nodes'][offset:i + 1]],
                                          oneway_flag)
                        neighbors.append(cur_way['nodes'][i]['node_id'])
                        break
        return prev_neighbors + neighbors

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

    def write_stats_to_screen(self):
        for char in self.lastStatString:
            sys.stdout.write('\b')
        self.lastStatString = str("%d ways have already analysed" % self.stat_ways)
        sys.stdout.write(self.lastStatString)


def haversine(point1, point2):
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
