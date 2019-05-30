# Поиск маршрутов без левых поворотов и разворотов
#### Requirements
- flask
- pymongo
- numpy
- overpy
- requests

#### Modules
- `astar` - модификация алгоритма А*
- `configuration` - класс конфигурации сервера
- `graph` - построение графа, поиск путей
- `osm_handler` - чтение и запись данных в MongoDB
- `server` - сервер для взаимодействия с клиентом
- `utils` - необходимые утилиты

#### Run
- Серверная часть:
    - Создать файл *`config.json`* из файла *`settings/config_example.json`*, заполнив поля “IP” и “port”.
    - Запустить MongoDB (используя стандартные настройки).
    - Установить необходимые python-зависимости из *`requirements.txt`*
    - Запустить файл *`server.py`* из каталога *`source`*, используя команду *`python3.7 server.py`*.
- Android-приложение
    - Выполнить команду *`gradlew assembleDebug`*
    - Apk-файл может быть найден в *`app/build/outputs/apk/app-debug.apk`*