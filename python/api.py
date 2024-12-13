
from datetime import datetime
import io
from typing import Union
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import utils
import milvus
import time
import clip1
import meili
from bson import ObjectId
import httpx


config = utils.get_config()
mongodb = utils.get_db(config)[0]
clip_ = clip1.CLIP1()
milivus_ = milvus.Milvus1(config)
meili_ = meili.Meili(config)

milvus_limit = 1200
mongodb_limit = 1200
meili_limit = 1200


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


async def process_img(image_data: bytes):
    image_pil = Image.open(io.BytesIO(image_data))
    print(f'Image received: {image_pil.format}, {image_pil.size}, {image_pil.mode}')
    start_get_clip_time = time.time()
    image_features = clip_.get_clip_result(image_pil)
    end_get_clip_time = time.time()
    print(f'get clip result time: {end_get_clip_time - start_get_clip_time}s')

    start_milvus_time = time.time()
    milvus_results = milivus_.search(image_features, milvus_limit)
    end_milvus_time = time.time()
    print(f'milvus search time: {end_milvus_time - start_milvus_time}s')
    ids = [result['id'] for result in milvus_results]
    return ids, milvus_results


async def process_docs(documents, distance_map, text_distance_map, meili_ids):
    if meili_ids:
        id_to_index = {id: index for index, id in enumerate(meili_ids, start=1)}
    for doc in documents:
        for date_field in ['date', 'createDate']:
            if date_field in doc and isinstance(doc[date_field], datetime):
                doc[date_field] = doc[date_field].strftime('%Y/%m/%d-%H:%M:%S')
        doc['_id'] = str(doc['_id'])
        if distance_map:
            doc['image_distance'] = distance_map.get(doc['_id'])
        if text_distance_map:
            doc['text_distance'] = text_distance_map.get(doc['_id'])
        if meili_ids:
            doc['meili_order'] = id_to_index.get(doc['_id'])

    documents.sort(key=lambda x: (
        -x.get('meili_order', 99999) if meili_ids else 99999,
        x.get('image_distance', -1) if distance_map else -1,
        x.get('text_distance', -1) if text_distance_map else -1
    ), reverse=True)

    return documents


@app.post('/api/query/')
async def query_mongodb(
    text: str | None = Form(None),
    query: str | None = Form(None),
    sort: str | None = Form(None),
    image: Union[UploadFile, str, None] = Form(None),
):

    print('text', text)
    print('query', query)
    print('sort', sort)
    print('image', type(image))
    start_time = time.time()
    mongo_query, meili_query, meili_tags1_query = utils.build_query([item.strip() for item in query.split(',')]) if query and query != 'null' else ({}, '', '')
    mongo_sort = utils.build_sort([item.strip() for item in sort.split(',')]) if sort and sort != 'null' else {}
    print('mongo_query', mongo_query)
    print('mongo_sort', mongo_sort)
    print('meili_query', meili_query)
    print('meili_tags1_query', meili_tags1_query)
    ids = text_ids = meili_ids = []
    milvus_results = milvus_text_results = []
    distance_map = text_distance_map = {}

    try:
        if isinstance(image, str):
            async with httpx.AsyncClient() as client:
                response = await client.get(image)
                image_data = response.content
        elif image and image != 'null':
            image_data = await image.read()
        else:
            image_data = None

        if image_data:
            ids, milvus_results = await process_img(image_data)

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={'error': f'Failed to process image: {str(e)}'},
        )


    if text and text != 'null':
        text_features = clip_.get_clip_text_result(text)
        milvus_text_results = milivus_.search(text_features, milvus_limit)
        text_ids = [result['id'] for result in milvus_text_results]


    if common_ids := set(ids) & set(text_ids) if ids and text_ids else set(ids) | set(text_ids):
        print('common_ids', len(common_ids))
        distance_map = {result['id']: result['distance'] for result in milvus_results if result['id'] in common_ids}
        text_distance_map = {result['id']: result['distance'] for result in milvus_text_results if result['id'] in common_ids}
    elif ids or text_ids:
        return []

    if meili_query:
        meili_results = meili_.search(meili_query, limit=meili_limit, attributesToSearchOn=['text'])
        meili_ids = [result['_id'] for result in meili_results['hits']]
        print('meili_ids', len(meili_ids))
        common_ids = set(common_ids) & set(meili_ids) if common_ids else set(meili_ids)
        if not common_ids:
            return []
        print('common_ids', len(common_ids))

    if meili_tags1_query:
        meili_tags1_results = meili_.search(meili_tags1_query, limit=meili_limit, attributesToSearchOn=['tags1'])
        meili_tags1_ids = [result['_id'] for result in meili_tags1_results['hits']]
        print('meili_tags1_ids', len(meili_tags1_ids))
        common_ids = set(common_ids) & set(meili_tags1_ids) if common_ids else set(meili_tags1_ids)
        if not common_ids:
            return []
        print('common_ids', len(common_ids))

    if common_ids:
        object_ids = {ObjectId(id_str) for id_str in common_ids}
        mongo_query['_id'] = {'$in': list(object_ids)}


    start_mongodb_time = time.time()
    if mongo_sort:
        documents = list(mongodb.find(mongo_query).sort(mongo_sort).limit(mongodb_limit))
    else:
        documents = list(mongodb.find(mongo_query).limit(mongodb_limit))
    end_mongodb_time = time.time()
    print(f'mongodb query time: {end_mongodb_time - start_mongodb_time}s')
    print('documents', len(documents))

    documents = await process_docs(documents, distance_map, text_distance_map, meili_ids)

    end_time = time.time()
    print(f'time: {end_time - start_time}s')

    return documents
