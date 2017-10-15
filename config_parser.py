import configparser, os

#config_path = os.path.join(os.path.dirname(__file__),'config.ini')

class ConfigParser:

    def __init__(self, path):
        self.config_path = path
        if not os.path.isfile(self.config_path):
            raise Exception('No config.ini at {0}!'.format(self.config_path))
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)

    def get(self, property):
        return self.config.get('app_source',property)

    def getSection(self, section):
        list = self.config.items(section)
        return [item[1] for item in list]

    def getLibSourceFiles(self, lib):
        files = self.config.get('libraries', lib)
        if files == 'None':
            return []
        return files.replace(' ', '').split(',')


