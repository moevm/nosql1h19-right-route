import json
import os
from routing.utils import singleton


@singleton
class Configuration:

    def __init__(self, path=os.path.join('../settings/config.json')):
        self.path = path
        self.server_info = None
        self.bounds = None
        self.backup_info = None
        self.load_config()

    def load_config(self):
        if os.path.exists(self.path):
            with open(self.path, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                    self.server_info = data['server_info']
                    self.bounds = data['bounds']
                    self.backup_info = data['backup_info']
        else:
            print("Конфигурационный файл не найден, path='" + self.path + "'")

    def save_config(self):
        with open(self.path, "w", encoding='utf8') as write_file:
            json.dump({
                "server_info": self.server_info,
                "bounds": self.bounds,
                "backup_info": self.backup_info
            }, write_file, indent=4, ensure_ascii=False)

    def get_ip(self):
        return self.server_info['IP']

    def get_port(self):
        return self.server_info['port']

    def get_bounds(self):
        return self.bounds

    def add_bounds(self, bounds):
        if bounds not in self.bounds:
            self.bounds.append(bounds)

    def set_bounds(self, bounds: list):
        self.bounds = bounds

    def get_backup_info(self):
        return self.backup_info

    def set_backup_info(self, info):
        self.backup_info = info


if __name__ == "__main__":
    config = Configuration()
    print(config.get_ip())
    print(config.get_port())
    print(config.get_bounds)
