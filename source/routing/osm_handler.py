import sys
import os
import pymongo
import json
from pymongo import MongoClient
from xml.etree.cElementTree import iterparse
import xml.etree.cElementTree as xml
from routing.utils import singleton


@singleton
class OsmHandler(object):

    def __init__(self, db_client):
        self.db_client = db_client
        self.create_indexes()

    def create_indexes(self):
        self.db_client.nodes.create_index([('loc', pymongo.GEO2D)])
        self.db_client.nodes.create_index([('id', pymongo.ASCENDING), ('version', pymongo.DESCENDING)])
        self.db_client.ways.create_index([('tags.highway', pymongo.ASCENDING)])
        self.db_client.ways.create_index([('id', pymongo.ASCENDING), ('version', pymongo.DESCENDING)])

    def fill_default(self, attrs):
        record = dict(_id=int(attrs['id']),
                      tags={})
        return record

    def parse(self, file_obj):
        nodes = []
        ways = []
        bounds = None

        context = iter(iterparse(file_obj, events=('start', 'end')))
        event, root = context.__next__()

        for (event, elem) in context:
            name = elem.tag
            attrs = elem.attrib

            if 'start' == event:
                """Parse the XML element at the start"""
                if name == 'bounds':
                    bounds = attrs
                if name == 'node':
                    record = self.fill_default(attrs)
                    loc = [float(attrs['lat']),
                           float(attrs['lon'])]
                    record['loc'] = loc
                elif name == 'tag':
                    if not record:
                        continue
                    k = attrs['k']
                    v = attrs['v']

                    def check_tag(tg):
                        if tg in ['highway', 'name:ru', 'name', 'oneway']:
                            return True
                        if 'addr' in tg:
                            return True
                        return False

                    if check_tag(k):
                        record['tags'][k] = v

                    def check_speed(tg):
                        dict = {
                            'RU:urban': 60,
                            'RU:rural': 90,
                            'RU:motorway': 110
                        }
                        if tg in dict:
                            return dict[tg]
                        else:
                            try:
                                speed = int(tg)
                            except ValueError:
                                speed = 60
                            return speed

                    if k == 'maxspeed':
                        record['tags'][k] = check_speed(v)

                elif name == 'way':
                    # Insert remaining nodes
                    if len(nodes) > 0:
                        try:
                            self.db_client.nodes.insert_many(nodes, ordered=False)
                        except pymongo.errors.BulkWriteError:
                            pass    # дублирование ключей возможно при импорте смежных зон
                        nodes = []

                    record = self.fill_default(attrs)
                    record['nodes'] = []
                elif name == 'nd':
                    ref = int(attrs['ref'])
                    record['nodes'].append(ref)
            elif 'end' == event:
                """Finish parsing an element
                (only really used with nodes, ways)"""
                if name == 'node':
                    if len(record['tags']) == 0:
                        del record['tags']
                    nodes.append(record)
                    if len(nodes) > 2500:
                        try:
                            self.db_client.nodes.insert_many(nodes, ordered=False)
                        except pymongo.errors.BulkWriteError:
                            pass    # дублирование ключей возможно при импорте смежных зон
                        nodes = []
                    record = {}
                elif name == 'way':
                    if len(record['tags']) == 0:
                        del record['tags']
                    nds = dict((rec['_id'], rec['loc']) for rec in
                               self.db_client.nodes.find({'_id': {'$in': record['nodes']}}, {'loc': 1, '_id': 1}))
                    for i, node in enumerate(record['nodes']):
                        if node in nds:
                            record['nodes'][i] = {
                                'node_id': node,
                                'loc': nds[node]
                            }
                        else:
                            print('node not found: ' + str(node))

                    ways.append(record)
                    if len(ways) > 2000:
                        try:
                            self.db_client.ways.insert_many(ways, ordered=False)
                        except pymongo.errors.BulkWriteError:
                            pass    # дублирование ключей возможно при импорте смежных зон
                        ways = []

                    record = {}
            elem.clear()
            root.clear()
        if len(nodes) > 0:
            try:
                self.db_client.nodes.insert_many(nodes, ordered=False)
            except pymongo.errors.BulkWriteError:
                pass  # дублирование ключей возможно при импорте смежных зон
        if len(ways) > 0:
            try:
                self.db_client.ways.insert_many(ways, ordered=False)
            except pymongo.errors.BulkWriteError:
                pass  # дублирование ключей возможно при импорте смежных зон
        return bounds

    def create_backup(self, bounds, path=os.path.join('..', 'settings', 'backup.json')):
        nodes = list(self.db_client.nodes.find({}))
        ways = list(self.db_client.ways.find({}))
        backup = {
            'bounds': bounds,
            'nodes': nodes,
            'ways': ways
        }
        with open(path, "w", encoding='utf-8') as write_file:
            json.dump(backup, write_file, indent=4, ensure_ascii=False)

    def load_backup(self, path=os.path.join('..', 'settings', 'backup.json')):
        self.db_client.nodes.drop()    # удаление прошлых данных из БД
        self.db_client.ways.drop()
        with open(path, "r", encoding='utf-8') as read_file:
            backup = json.load(read_file)
        nodes = backup['nodes']
        ways = backup['ways']
        offset = 0
        while offset < len(nodes):
            self.db_client.nodes.insert_many(nodes[offset:offset + 1000])
            offset = offset + 1000
        offset = 0
        while offset < len(ways):
            self.db_client.ways.insert_many(ways[offset:offset + 1000])
            offset = offset + 1000
        self.create_indexes()
        return backup['bounds']


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: %s <OSM filename>" % (sys.argv[0]))
        sys.exit(-1)

    filename = sys.argv[1]

    if not os.path.exists(filename):
        print("Path %s doesn't exist." % filename)
        sys.exit(-1)

    client = MongoClient()
    client.drop_database("osm")  # полное обновление бд
    handler = OsmHandler(client.osm)
    handler.parse(open(filename, encoding='utf-8'))
    client.close()
