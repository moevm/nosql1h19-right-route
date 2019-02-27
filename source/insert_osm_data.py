import sys
import os
import pymongo
from pymongo import MongoClient
from xml.etree.cElementTree import iterparse


class OsmHandler(object):

    def __init__(self, client):
        self.client = client

        self.client.osm.nodes.create_index([('loc', pymongo.GEO2D)])
        self.client.osm.nodes.create_index([('id', pymongo.ASCENDING),
                                            ('version', pymongo.DESCENDING)])

        self.client.osm.ways.create_index([('loc', pymongo.GEO2D)])
        self.client.osm.ways.create_index([('id', pymongo.ASCENDING),
                                           ('version', pymongo.DESCENDING)])

        self.client.osm.relations.create_index([('id', pymongo.ASCENDING),
                                                ('version', pymongo.DESCENDING)])
        self.stat_nodes = 0
        self.stat_ways = 0
        self.stat_relations = 0
        self.lastStatString = ""
        self.statsCount = 0

    def write_stats_to_screen(self):
        for char in self.lastStatString:
            sys.stdout.write('\b')
        self.lastStatString = "%d nodes, %d ways, %d relations" % (self.stat_nodes,
                                                                   self.stat_ways,
                                                                   self.stat_relations)
        sys.stdout.write(self.lastStatString)

    def fillDefault(self, attrs):
        record = dict(_id=int(attrs['id']),
                      ts=attrs['timestamp'] if 'timestamp' in attrs else None,
                      tg=[],
                      ky=[])
        if 'user':
            record['un'] = attrs['user']
        if 'uid' in attrs:
            record['ui'] = int(attrs['uid'])
        if 'version' in attrs:
            record['v'] = int(attrs['version'])
        if 'changeset' in attrs:
            record['ch'] = int(attrs['changeset'])
        return record

    def parse(self, file_obj):
        nodes = []
        ways = []

        context = iter(iterparse(file_obj, events=('start', 'end')))
        event, root = context.__next__()

        for (event, elem) in context:
            name = elem.tag
            attrs = elem.attrib

            if 'start' == event:
                """Parse the XML element at the start"""
                if name == 'node':
                    record = self.fillDefault(attrs)
                    loc = [float(attrs['lat']),
                           float(attrs['lon'])]
                    record['loc'] = loc
                elif name == 'tag':
                    k = attrs['k']
                    v = attrs['v']
                    record['tg'].append((k, v))
                    record['ky'].append(k)
                elif name == 'way':
                    # Insert remaining nodes
                    if len(nodes) > 0:
                        self.client.osm.nodes.insert_many(nodes)
                        nodes = []

                    record = self.fillDefault(attrs)
                    record['nd'] = []
                elif name == 'relation':
                    # Insert remaining ways
                    if len(ways) > 0:
                        self.client.osm.ways.insert_many(ways)
                        ways = []

                    record = self.fillDefault(attrs)
                    record['mm'] = []
                elif name == 'nd':
                    ref = int(attrs['ref'])
                    record['nd'].append(ref)
                elif name == 'member':
                    record['mm'].append(dict(type=attrs['type'], ref=int(attrs['ref']), role=attrs['role']))

                    if attrs['type'] == 'way':
                        ways2relations = self.client.osm.ways.find_one({'_id': ref})
                        if ways2relations:
                            if 'relations' not in ways2relations:
                                ways2relations['relations'] = []
                            ways2relations['relations'].append(record['_id'])
                            self.client.osm.ways.save_many(ways2relations)
                    elif attrs['type'] == 'node':
                        nodes2relations = self.client.osm.nodes.find_one({'_id': ref})
                        if nodes2relations:
                            if 'relations' not in nodes2relations:
                                nodes2relations['relations'] = []
                            nodes2relations['relations'].append(record['_id'])
                            self.client.osm.nodes.replace_one({'_id': nodes2relations['_id']}, nodes2relations,
                                                              upsert=True)
            elif 'end' == event:
                """Finish parsing an element
                (only really used with nodes, ways and relations)"""
                if name == 'node':
                    if len(record['tg']) == 0:
                        del record['tg']
                    if len(record['ky']) == 0:
                        del record['ky']
                    nodes.append(record)
                    if len(nodes) > 2500:
                        self.client.osm.nodes.insert_many(nodes)
                        nodes = []
                        self.write_stats_to_screen()

                    record = {}
                    self.stat_nodes = self.stat_nodes + 1
                elif name == 'way':
                    if len(record['tg']) == 0:
                        del record['tg']
                    if len(record['ky']) == 0:
                        del record['ky']
                    nds = dict((rec['_id'], rec) for rec in
                               self.client.osm.nodes.find({'_id': {'$in': record['nd']}}, {'loc': 1, '_id': 1}))
                    record['loc'] = []
                    for node in record['nd']:
                        if node in nds:
                            record['loc'].append(nds[node]['loc'])
                        else:
                            print('node not found: ' + str(node))

                    ways.append(record)
                    if len(ways) > 2000:
                        self.client.osm.ways.insert_many(ways)
                        ways = []

                    record = {}
                    self.statsCount = self.statsCount + 1
                    if self.statsCount > 1000:
                        self.write_stats_to_screen()
                        self.statsCount = 0
                    self.stat_ways = self.stat_ways + 1
                elif name == 'relation':
                    if len(record['tg']) == 0:
                        del record['tg']
                    if len(record['ky']) == 0:
                        del record['ky']
                    self.client.osm.relations.insert_one(record)  # save => insert_one
                    record = {}
                    self.statsCount = self.statsCount + 1
                    if self.statsCount > 10:
                        self.write_stats_to_screen()
                        self.statsCount = 0
                    self.stat_relations = self.stat_relations + 1
            elem.clear()
            root.clear()


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
    handler = OsmHandler(client)
    handler.parse(open(filename, encoding='utf-8'))
    handler.write_stats_to_screen()
    client.close()
