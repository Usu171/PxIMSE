import httpx
import datetime


headers = {
    "Accept-Language": "zh-CN,zh;q=0.9",
}


async def fetch_illust_data(illust_id):
    url = f'https://www.pixiv.net/ajax/illust/{illust_id}'

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f'HTTP Error: {e.response.status_code} - {e.response.text} id: {illust_id}')
            return None
        except httpx.RequestError as e:
            print(f'Error: {e} id: {illust_id}')
            return None

    data = response.json()

    if data['error']:
        print(f'Data Error: id: {illust_id}')
        return None

    body = data['body']

    illust_data = {
        'userid': body['userId'],
        'title': body['illustTitle'],
        'user': body['userName'],
        'description': body['description'],
        'createDate': datetime.datetime.fromisoformat(body['createDate']),
        'viewCount': body['viewCount'],
        'bookmarkCount': body['bookmarkCount'],
        'likeCount': body['likeCount'],
        'commentCount': body['commentCount'],
        'tags1': [
            item
            for tag in body['tags']['tags']
            for item in (tag['tag'], tag.get('translation', {}).get('en')) if item
        ]
    }

    return illust_data
