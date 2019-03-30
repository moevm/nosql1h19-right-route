import sys
from haversine import haversine
from astar import AStar


class Graph(AStar):

    def __init__(self, client):
        self.mongo_client = client
        self.tags = [['highway', 'motorway'], ['highway', 'motorway_link'], ['highway', 'trunk'],
                     ['highway', 'trunk_link'], ['highway', 'primary'], ['highway', 'primary_link'],
                     ['highway', 'secondary'], ['highway', 'secondary_link'], ['highway', 'tertiary'],
                     ['highway', 'tertiary_link'], ['highway', 'unclassified'], ['highway', 'residential']
                     ]
        self.lastStatString = ""
        self.stat = 0

    def creating(self):
        """
        Создание графа путей
        :return: -
        """
        # отчистка узлов от графа
        self.delete_graph()
        self.write_stats_to_screen()
        # одним запросом выгрузить все необходимые пути
        ways = list(self.mongo_client.osm.ways.find({'tg': {'$in': self.tags}},
                                                    {'_id': 1, 'nd': 1, 'loc': 1, 'tg': 1, 'ky': 1}))
        self.stat = 0  # счётчик проанализированных путей
        # Обход всех путей
        for cur_way in ways:  # проанализировать каждый путь
            way_tag = cur_way['tg'][cur_way['ky'].index('highway')][1]
            self.stat = self.stat + 1
            if self.stat % 100 == 0:
                self.write_stats_to_screen()
            oneway_flag = 'oneway' in cur_way['ky']  # если односторонее движение (понадобится позже)
            last_shared_node = 0
            for i, node in enumerate(cur_way['nd']):  # проанализировать каждый узел пути
                count_ways = self.mongo_client.osm.ways.count_documents(
                    {'_id': {'$ne': cur_way['_id']}, 'nd': node, 'tg': {'$in': self.tags}})
                # теги для того, чтобы не учитывать узлы-пересечения c ненужными путями
                if count_ways > 0 and last_shared_node != i:
                    # найдена новая вершина - записать соседа и просчитать длину ребра
                    self.add_neighbor(cur_way['_id'], way_tag, cur_way['nd'][last_shared_node], cur_way['nd'][i],
                                      cur_way['loc'][last_shared_node:i + 1], oneway_flag)
                    last_shared_node = i  # сменить вершину последнего пересечения для нового ребра
        self.write_stats_to_screen()
        print()

    def add_neighbor(self, way_id, way_tag, id_from, id_to, locs, oneway_flag):
        """
        Добавление соседа узла
        :param way_id: id пути, соединяющего узлы
        :param way_tag: тег пути, соединяющего узлы
        :param id_from: id узла, из которого идём
        :param id_to: id узла, в который идём
        :param locs: координаты узлов между начальным и конечным узлом
        :param oneway_flag: флаг одностороннего движения
        :return: -
        """
        length = 0
        for i, loc in enumerate(locs):
            if i == len(locs) - 1:
                break
            length = length + haversine(loc, locs[i + 1])  # расчёт длины по точкам (на случай криволинейности)
        # хранение информации о соседях в узле
        self.mongo_client.osm.nodes.update_one(
            {'_id': id_from},
            {
                '$push':
                    {
                        'to': id_to,
                        'distances': length,
                        'ways': way_id,
                        'way_tag': way_tag,
                    }
            }
        )
        if not oneway_flag:  # если путь не односторонний - добавление обратного
            self.mongo_client.osm.nodes.update_one(
                {'_id': id_to},
                {
                    '$push':
                        {
                            'to': id_from,
                            'distances': length,
                            'ways': way_id,
                            'way_tag': way_tag
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
        dist = self.mongo_client.osm.nodes.find_one({'_id': node_id1, 'to': node_id2}, {'to': 1, 'distances': 1})
        # fixme исключение - между двумя точками есть больше 1 пути (например, круговое)
        #  пока берём первый
        return dist['distances'][dist['to'].index(node_id2)]

    def heuristic_cost_estimate(self, n1, n2):
        return 0

    def neighbors(self, node):
        """
        Соседи узла
        :param node: id узла
        :return: list(ids соседей)
        """
        neighbors = self.mongo_client.osm.nodes.find_one({'_id': node})
        if 'to' in neighbors:
            return neighbors['to']
        else:
            return []

    def delete_graph(self):
        """
        Удаление данных о графе из БД
        :return: -
        """
        self.mongo_client.osm.nodes.update_many({'to': {'$exists': 1}},
                                                {
                                                    '$unset':
                                                        {
                                                            'to': "",
                                                            'ways': "",
                                                            'distances': "",
                                                            'way_tag': "",
                                                        }
                                                }
                                                )

    def write_stats_to_screen(self):
        for char in self.lastStatString:
            sys.stdout.write('\b')
        self.lastStatString = str("%d ways have already analysed" % self.stat)
        sys.stdout.write(self.lastStatString)


from pymongo import MongoClient

if __name__ == '__main__':
    mongo = MongoClient()
    map_graph = Graph(mongo)
    map_graph.creating()  # создание графа

    # обычный путь
    path = map_graph.astar(5002127528, 297813224)
    if path:
        path = list(path)
    else:
        path = []
    path_length = 0
    for i, node in enumerate(path):
        if i == len(path) - 1:
            break
        path_length = path_length + map_graph.distance_between(node, path[i + 1])
    print('Dist = ', str(path_length), ' km')
    print('Path = ', end='')
    print(path)

    # путь без левых поворотов и разворотов
    path = map_graph.astar(5002127528, 297813224, nodes_client_for_left=map_graph.mongo_client.osm.nodes)
    if path:
        path = list(path)
    else:
        path = []
    path_length = 0
    for i, node in enumerate(path):
        if i == len(path) - 1:
            break
        path_length = path_length + map_graph.distance_between(node, path[i + 1])
    print('Dist = ' + str(path_length), ' km')
    print('Path = ', end='')
    print(path)

    mongo.close()
