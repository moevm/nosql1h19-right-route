# nosql1h19-right-route
#### Requirements
- pymongo
- haversine

#### Modules
- `astar.py` - модификация алгоритма А*
- `graph` - построение графа, поиск путей
- `osm_handler` - чтение *.osm и запись в MongoDB

#### Overview
Подключение к БД и запуск парсинга *.osm файла. (Перед повторным парсингом необходимо удалить БД: `mongo_client.drop_database('osm')`)
```python
import osm_handler
import graph
from pymongo import MongoClient
mongo_client = MongoClient()
handler = osm_handler.OsmHandler(mongo_client)handler.parse(open('<path to *.osm>', encoding='utf-8'))
```

Создание графа дорог на основе данных, хранящихся в БД.
```python
map_graph = graph.Graph(mongo_client)
map_graph.creating()
```

Поиск пути между двумя узлами, содержащимися в графе - не любой узел можно использовать для поиска.
```python
path = map_graph.astar(from_id_node, to_id_node)
```

Поиск пути без левых поворотов и разворотов между двумя узлами, содержащимися в графе.
```python
path = map_graph.astar(from_id_node, to_id_node, nodes_client_for_left=map_graph.mongo_client.osm.nodes)
```
