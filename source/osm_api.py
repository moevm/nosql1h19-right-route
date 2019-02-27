from pymongo import MongoClient


class OsmApi:
    def __init__(self):
        self.client = MongoClient()

    def get_node_by_id(self, id):
        cursor = self.client.osm.nodes.find_one({'_id': id})
        if cursor:
            return {'nodes': [cursor]}
        else:
            return {}

    def get_way_by_id(self, id):
        cursor = self.client.osm.ways.find_one({'_id': id})
        if cursor:
            return {'ways': [cursor]}
        else:
            return {}

    def get_relation_by_id(self, id):
        cursor = self.client.osm.relations.ways.find_one({'_id': id})
        if cursor:
            return {'relations': [cursor]}
        else:
            return {}

    def get_nodes_by_request(self, req: dict):
        cursor = api.client.osm.nodes.find(req)
        nodes = {}
        for row in cursor:
            nodes[row['_id']] = row
        return nodes

    def get_ways_by_request(self, req: dict):
        cursor = api.client.osm.ways.find(req)
        ways = {}
        for row in cursor:
            ways[row['_id']] = row
        return ways

    def get_relations_by_request(self, req: dict):
        cursor = api.client.osm.relations.find(req)
        relations = {}
        for row in cursor:
            relations[row['_id']] = row
        return relations


if __name__ == '__main__':
    api = OsmApi()

    print(api.get_node_by_id(id=18702726))

    tmp = api.get_nodes_by_request({'un': 'Sergey Astakhov'})
    print(tmp)
    print(len(tmp))

    tmp = api.get_nodes_by_request({'un': 'Unexisted User'})
    print(tmp)
    print(len(tmp))

    tmp = api.get_ways_by_request({'un': 'Sergey Astakhov'})
    print(tmp)
    print(len(tmp))

    tmp = api.get_ways_by_request({'un': 'Unexisted User'})
    print(tmp)
    print(len(tmp))

    tmp = api.get_relations_by_request({'un': 'Sergey Astakhov'})
    print(tmp)
    print(len(tmp))

    tmp = api.get_relations_by_request({'un': 'Unexisted User'})
    print(tmp)
    print(len(tmp))
