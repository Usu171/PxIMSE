from meilisearch import Client
import utils


class Meili():
    
    def __init__(self, config):
        self.index = config['meilisearch-index']
        self.client = Client(f'http://{config["meilisearch-host"]}:{config["meilisearch-port"]}', config['meilisearch-master-key'])
    
    def update_documents(self, documents, primary_key):
        return self.client.index(self.index).update_documents(documents, primary_key)
    
    def search(self, query, limit=1200, offset=0):
        return self.client.index(self.index).search(query, {'limit': limit, 'offset': offset})
