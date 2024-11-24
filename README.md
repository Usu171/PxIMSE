# PxIMSE

Local [Pixiv](https://www.pixiv.net/) image search based on [DeepDanbooru](https://github.com/KichangKim/DeepDanbooru) and [CLIP](https://github.com/openai/CLIP)

![](assets/1.jpg)


### Supported file name formats

Images from [Pixiv](https://www.pixiv.net/), [PixivBatchDownloader](https://github.com/xuejianxianzun/PixivBatchDownloader), [PixEZ](https://github.com/Notsfsssf/pixez-flutter) ... , [Twitter Media Downloader](https://greasyfork.org/zh-CN/scripts/423001-twitter-media-downloader), [yande.re](https://yande.re/): 
- pixiv: {user_id}_{id}_p{index}
- pixiv: {id}_p{index}
- twitter: twitter_{user_name}(@{user_id})_{date}_{id}_photo
- yande.re: yande.re {id} {tags}

## Prerequisites

- [MongoDB](https://www.mongodb.com/)
- [Milvus](https://milvus.io/)
- [Nginx](https://nginx.org/)
- [Pre-trained DeepDanbooru model](https://github.com/KichangKim/DeepDanbooru/releases/tag/v3-20211112-sgd-e28)

## Usage

### Import image information

After configuring config and installing dependencies:


Import image information, DeepDanbooru and OCR results to MongoDB
```sh
python import_images.py mongo
```

Import CLIP results to Milvus

```sh
python import_images.py milvus
```

Get information from Pixiv website (optional)
```sh
python import_images.py pixiv
```

Attempt to assign the username from an existing document in the database to a document with the same user ID that doesn't have a username (Indexes must be created on the username and userid fields)

```sh
python import_images.py update

```

### Start Service


```sh
uvicorn api:app --host 0.0.0.0 --port 8000
```
```sh
pnpm dev
```

### Format of Query Criteria

**Exists:**  
tags.xxx  
tags1:xxx

**Does not exist:**  
!tags.xxx  
!tags1:xxx

**Greater than, less than, equal to, not equal to:**  
date;>2000-01-01&<2010-01-01  
likeCount;=100  
viewCount;!=200  

**Text length:**  
textlen;>xx



tags are obtained from DeepDanbooru  
tags1 are retrieved from Pixiv website (For yandere, from the file name)
