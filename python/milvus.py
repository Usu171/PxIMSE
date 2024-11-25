from pymilvus import connections, db, Collection, MilvusClient
from pymilvus import FieldSchema, CollectionSchema, DataType
import utils

config = utils.get_config()

conn = connections.connect(
    host=config['milvusdb-host'], port=config['milvusdb-port'])

if config['milvusdb-db'] not in db.list_database():
    db.create_database(config['milvusdb-db'])
    db.using_database(config['milvusdb-db'])
    fields = [
        FieldSchema(
            name="id",
            dtype=DataType.VARCHAR,
            is_primary=True,
            auto_id=False,
            max_length=24),
        FieldSchema(name="clip", dtype=DataType.FLOAT16_VECTOR, dim=512) # FP16
        # ViT-B/32: 512, ViT-L/14: 768
    ]
    schema = CollectionSchema(fields, auto_id=False)
    collection = Collection(name=config['milvusdb-collection'], schema=schema)
    collection = Collection('imgs')

    collection.create_index(field_name="id", index_name="id1")
    index_params = {
        "index_type": "HNSW",
        "metric_type": "IP",  # COSINE, L2, IP
        "params": {
            "M": 32,
            "efConstruction": 64
        }
    }

    collection.create_index(
        field_name="clip", index_params=index_params, index_name="clip1")


class Milvus1():

    def __init__(self, config):
        self.config = config
        self.collection = config['milvusdb-collection']
        self.client = MilvusClient(
            uri='http://{}:{}'.format(config['milvusdb-host'],
                                      config['milvusdb-port']),
            db_name=config['milvusdb-db'])
        self.client.load_collection(collection_name=self.collection)

    def insert(self, id, clip_data):
        data = {'id': id, 'clip': clip_data}
        return self.client.insert(collection_name=self.collection, data=data)

    def get(self, _id):
        return self.client.get(collection_name=self.collection, ids=_id)

    def query(self, query):
        return self.client.query(collection_name=self.collection, filter=query)

    def search(self, data, limit):
        data = [data]
        return self.client.search(
            collection_name=self.collection, data=data, limit=limit
        )[0]
