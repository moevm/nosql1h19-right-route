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

        self.db_client.nodes.create_index([('loc', pymongo.GEO2D)])
        self.db_client.nodes.create_index([('id', pymongo.ASCENDING),
                                            ('version', pymongo.DESCENDING)])

        self.db_client.ways.create_index([('loc', pymongo.GEO2D)])
        self.db_client.ways.create_index([('id', pymongo.ASCENDING),
                                           ('version', pymongo.DESCENDING)])

        self.stat_nodes = 0
        self.stat_ways = 0
        self.lastStatString = ""
        self.statsCount = 0

    def write_stats_to_screen(self):
        return None
        for char in self.lastStatString:
            sys.stdout.write('\b')
        self.lastStatString = "%d nodes, %d ways" % (self.stat_nodes, self.stat_ways)
        sys.stdout.write(self.lastStatString)

    def fillDefault(self, attrs):
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
                    record = self.fillDefault(attrs)
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
                elif name == 'way':
                    # Insert remaining nodes
                    if len(nodes) > 0:
                        self.db_client.nodes.insert_many(nodes)
                        nodes = []

                    record = self.fillDefault(attrs)
                    record['nodes'] = []
                elif name == 'relation':
                    continue
                elif name == 'nd':
                    ref = int(attrs['ref'])
                    record['nodes'].append(ref)
                elif name == 'member':
                    continue
            elif 'end' == event:
                """Finish parsing an element
                (only really used with nodes, ways)"""
                if name == 'node':
                    if len(record['tags']) == 0:
                        del record['tags']
                    nodes.append(record)
                    if len(nodes) > 2500:
                        self.db_client.nodes.insert_many(nodes)
                        nodes = []
                        self.write_stats_to_screen()

                    record = {}
                    self.stat_nodes = self.stat_nodes + 1
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
                        self.db_client.ways.insert_many(ways)
                        ways = []

                    record = {}
                    self.statsCount = self.statsCount + 1
                    if self.statsCount > 1000:
                        self.write_stats_to_screen()
                        self.statsCount = 0
                    self.stat_ways = self.stat_ways + 1
                elif name == 'relation':
                    continue
            elem.clear()
            root.clear()
        return bounds


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
    handler.write_stats_to_screen()
    client.close()
