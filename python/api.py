
from datetime import datetime
import io
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import utils
import milvus
import time
import clip1


config = utils.get_config()
mongodb = utils.get_db(config)[0]
clip_ = clip1.CLIP1()
milivus_ = milvus.Milvus1(config)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.post('/api/query/')
async def query_mongodb(
    text: str | None = Form(None),
    query: str | None = Form(None),
    sort: str | None = Form(None),
    image: UploadFile | None = Form(None),
):

    print('text', text)
    print('query', query)
    print('sort', sort)
    start_time = time.time()
    mongo_query = utils.build_query([item.strip() for item in query.split(',')]) if query and query != 'null' else {}
    mongo_sort = utils.build_sort([item.strip() for item in sort.split(',')]) if sort and sort != 'null' else {}
    print('mongo_query', mongo_query)
    print('mongo_sort', mongo_sort)
    ids = text_ids = []
    milvus_results = milvus_text_results = []
    distance_map = text_distance_map = {}


    if image and image != 'null':
        try:
            image_data = await image.read()
            image_pil = Image.open(io.BytesIO(image_data))
            print(f'Image received: {image_pil.format}, {image_pil.size}, {image_pil.mode}')
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={'error': f'Failed to process image: {str(e)}'},
            )
        start_get_clip_time = time.time()
        image_features = clip_.get_clip_result(image_pil)
        end_get_clip_time = time.time()
        print(f'get clip result time: {end_get_clip_time - start_get_clip_time}s')

        start_milvus_time = time.time()
        milvus_results = milivus_.search(image_features, 16384)
        end_milvus_time = time.time()
        print(f'milvus search time: {end_milvus_time - start_milvus_time}s')
        ids = [result["id"] for result in milvus_results]

    if text and text != 'null':
        text_features = clip_.get_clip_text_result(text)
        milvus_text_results = milivus_.search(text_features, 16384)
        text_ids = [result["id"] for result in milvus_text_results]


    if common_ids := set(set(ids) & set(text_ids)) if ids and text_ids else set(set(ids) | set(text_ids)):
        distance_map = {result["id"]: result["distance"] for result in milvus_results if result["id"] in common_ids}
        text_distance_map = {result["id"]: result["distance"] for result in milvus_text_results if result["id"] in common_ids}

    start_mongodb_time = time.time()
    if mongo_sort:
        documents = list(mongodb.find(mongo_query).sort(mongo_sort).limit(10000))
    else:
        documents = list(mongodb.find(mongo_query).limit(10000))
    end_mongodb_time = time.time()
    print(f'mongodb query time: {end_mongodb_time - start_mongodb_time}s')
    print('documents', len(documents))
    for doc in documents:
        if 'date' in doc and isinstance(doc['date'], datetime):
            doc['date'] = doc['date'].strftime('%Y/%m/%d-%H:%M:%S')
        if 'createDate' in doc and isinstance(doc['createDate'], datetime):
            doc['createDate'] = doc['createDate'].strftime('%Y/%m/%d-%H:%M:%S')
        doc['_id'] = str(doc['_id'])
        if distance_map:
            doc['image_distance'] = distance_map.get(doc['_id'])
        if text_distance_map:
            doc['text_distance'] = text_distance_map.get(doc['_id'])
    if distance_map and not text_distance_map:
        documents.sort(key=lambda x: x['image_distance'] if x['image_distance'] is not None else 0, reverse=True)
    elif text_distance_map and not distance_map:
        documents.sort(key=lambda x: x['text_distance'] if x['text_distance'] is not None else 0, reverse=True)
    elif distance_map:
        documents.sort(key=lambda x: (x['image_distance'] if x['image_distance'] is not None else 0,
                                        x['text_distance'] if x['text_distance'] is not None else 0),
                                        reverse=True)

    end_time = time.time()
    print(f'time: {end_time - start_time}s')


    return documents
