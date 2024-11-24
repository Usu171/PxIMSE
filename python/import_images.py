from glob import glob
import utils
import pixiv
from tqdm import tqdm
import os
from natsort import natsorted
from pathlib import Path
import sys
from PIL import Image, PngImagePlugin, ImageFile
from datetime import datetime
import concurrent.futures
import asyncio

nonedoc = {
    'filename': None,
    'folder': None,
    'type': None,
    'width': None,
    'height': None,
    'filesize': None,
    'date': None,

    'title': None,
    'user': None,
    'userid': None,
    'illustid': None,

    'description': None,
    'createDate': None,
    'viewCount': None,
    'bookmarkCount': None,
    'likeCount': None,
    'commentCount': None,

    'tags': None,
    'tags1': None,

    'text':None
    #'feature'
}


PngImagePlugin.MAX_TEXT_CHUNK = 2**22
ImageFile.LOAD_TRUNCATED_IMAGES = True


def import_imgs(config, operation, mongodb, *args):
    total_folders = len(config['folders'])
    for idx, folder in enumerate(config['folders'], start=1):
        folder_name = folder['name']
        folder_path = folder['path']
        print(f'Processing folder {idx}/{total_folders}: {folder_name}, Path: {folder_path}')
        filelist = glob(os.path.join(folder_path, '*'), recursive=True)
        # filelist = natsorted([
        #     f for f in filelist
        #     if os.path.isfile(f) and f.lower().endswith(('.png', '.jpg',
        #                                                  '.jpeg', '.gif',
        #                                                  '.webp'))
        # ], reverse=False)
        filelist = sorted(
            [f for f in filelist if os.path.isfile(f) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))],
            key=os.path.getmtime,
            reverse=True
        )
        max_threads = 4
        with tqdm(total=len(filelist)) as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = [
                    executor.submit(import_function, operation, file, folder_name, mongodb, pbar, *args)
                    for file in filelist
                ]
                for future in concurrent.futures.as_completed(futures):
                    future.result()


def import_function(operation, file, folder_name, mongodb, pbar, *args):
    func = operation_functions.get(operation, import_mongo)
    res = func(file, folder_name, mongodb, *args)
    pbar.update(1)
    return res

def import_mongo(file, folder_name, mongodb, ocr_, dd_):
    filename = Path(file).name
    filename1 = filename.encode('utf-8', errors='ignore').decode('utf-8')
    if existing_doc := mongodb[0].find_one({'filename': filename1, 'folder': folder_name}):
        _id = str(existing_doc['_id'])
        print(f'Document found with id: {_id}')
        return
    file_type = utils.get_file_type(filename1)
    filename_info = utils.get_filename_info(filename1, file_type)

    print(f'file:{filename1}')
    try:
        image = Image.open(file).convert('RGB')
    except Exception:
        print('Error:', filename1)
        if not mongodb[1].find_one({'filename': filename1, 'folder': folder_name}):
            mongodb[1].insert_one({'filename': filename1, 'folder': folder_name})
        return

    width, height = image.size

    file_size = os.path.getsize(file)
    try:
        m_time = os.path.getmtime(file)
        m_datetime = datetime.fromtimestamp(m_time)
    except Exception:
        m_datetime = None

    ocr_text = ocr_.get_ocr_result(file, 0.7)

    tags = dd_.predict_tags(image, 0.5)

    file_info = {
        'filename': filename1,
        'folder': folder_name,
        'type': file_type,
        'width': width,
        'height': height,
        'filesize': file_size,
        'date': m_datetime,
        'tags': tags,
        'text': ocr_text
}

    document = {**nonedoc, **filename_info, **file_info}

    result = mongodb[0].insert_one(document)
    _id = str(result.inserted_id)
    print(f'Insertion Successful id: {_id}')


def import_milvus(file, folder_name, mongodb, clip1_, milvus_):
    filename = Path(file).name
    filename1 = filename.encode('utf-8', errors='ignore').decode('utf-8')
    existing_doc = mongodb[0].find_one({'filename': filename1, 'folder': folder_name})
    if not existing_doc:
        print(f'Not Found: {filename1} {folder_name}')
        if not mongodb[1].find_one({'filename': filename1, 'folder': folder_name, 'NotFound': True}):
            mongodb[1].insert_one({'filename': filename1, 'folder': folder_name , 'NotFound': True})
        return

    _id = str(existing_doc['_id'])

    if existing_doc := milvus_.get(_id):
        print(f'Document found with id: {_id}')
        return

    print(f'file:{filename1}')
    try:
        image = Image.open(file).convert('RGB')
    except Exception:
        print('Error:', filename1)
        if not mongodb[1].find_one({'filename': filename1, 'folder': folder_name}):
            mongodb[1].insert_one({'filename': filename1, 'folder': folder_name})
        return

    clip_result = clip1_.get_clip_result(image)
    milvus_.insert(_id, clip_result)
    print(f'Insertion Successful id: {_id}')


def import_pixiv(file, folder_name, mongodb):
    filename = Path(file).name
    filename1 = filename.encode('utf-8', errors='ignore').decode('utf-8')
    file_type = utils.get_file_type(filename1)
    if 'pixiv' not in file_type:
        print(f'Not a pixiv file: {filename1} {folder_name}')
        return
    existing_doc = mongodb[0].find_one({'filename': filename1, 'folder': folder_name})
    if not existing_doc:
        print(f'Not Found in DB: {filename1} {folder_name}')
        if not mongodb[1].find_one({'filename': filename1, 'folder': folder_name, 'NotFound': True}):
            mongodb[1].insert_one({'filename': filename1, 'folder': folder_name , 'NotFound': True})
        return
    if existing_doc['title']:
        print(f'Pixiv information already exists in DB: {filename1} {folder_name}')
        return
    _id = existing_doc['_id']
    illustid = existing_doc['illustid']
    if mongodb[1].find_one({'filename': filename1, 'folder': folder_name, 'pixiv': True}):
        print(f'Pixiv information not found in past records: {filename1} {folder_name} id: {illustid}')
        return

    if matching_doc := mongodb[0].find_one(
        {'illustid': illustid, 'title': {'$ne': None}}
    ):
        update_fields = {
            'title': matching_doc['title'],
            'user': matching_doc['user'],
            'description': matching_doc['description'],
            'createDate': matching_doc['createDate'],
            'viewCount': matching_doc['viewCount'],
            'bookmarkCount': matching_doc['bookmarkCount'],
            'likeCount': matching_doc['likeCount'],
            'commentCount': matching_doc['commentCount'],
            'tags1': matching_doc['tags1']
        }
        mongodb[0].update_one(
            {'_id': _id},
            {'$set': update_fields}
        )
        print(f'Find information in other documents: {filename1} {folder_name} id: {illustid}')
    elif illust_info := asyncio.run(pixiv.fetch_illust_data(illustid)):
        mongodb[0].update_one(
            {'_id': _id},
            {'$set': illust_info}
        )
        print(f'Update Successful: {filename1} {folder_name} id: {illustid}')
    else:
        print(f'Pixiv information not found: {filename1} {folder_name} id: {illustid}')
        if not mongodb[1].find_one({'filename': filename1, 'folder': folder_name , 'pixiv': True}):
            mongodb[1].insert_one({'filename': filename1, 'folder': folder_name , 'pixiv': True})


def update(mongodb):
    from pymongo import UpdateMany
    pipeline = [
        {'$match': {'user': {'$ne': None}}},
        {'$group': {'_id': '$userid', 'user': {'$first': '$user'}}}
    ]

    result = mongodb[0].aggregate(pipeline)

    bulk_ops = [
        UpdateMany(
            {'userid': doc['_id'], 'user': None},
            {'$set': {'user': doc['user']}},
        )
        for doc in result
    ]

    if bulk_ops:
        mongodb[0].bulk_write(bulk_ops)
        print('Update Successful')


operation_functions = {
    'mongo': import_mongo,
    'milvus': import_milvus,
    'pixiv': import_pixiv
}


def main():
    if len(sys.argv) < 2:
        print('Error: No operation specified.')
        sys.exit(1)
    config = utils.get_config()
    mongodb = utils.get_db(config)

    match sys.argv[1]:
        case 'mongo':
            import dd1
            import ocr
            ocr_ = ocr.POCR()
            dd_ = dd1.DD1(config)
            import_imgs(config, 'mongo', mongodb, ocr_ , dd_)
        case 'milvus':
            import clip1
            import milvus
            clip1_ = clip1.CLIP1()
            milivus_ = milvus.Milvus1(config)
            import_imgs(config, 'milvus', mongodb, clip1_, milivus_)
        case 'pixiv':
            import_imgs(config, 'pixiv', mongodb)
        case 'update':
            update(mongodb)
        case _:
            print('Invalid operation specified.')



if __name__ == '__main__':
    main()
