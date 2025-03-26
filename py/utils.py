import requests as rq
import unicodedata
from bs4 import BeautifulSoup as bs
from requests import Session
from requests_cache import CacheMixin
from requests_ratelimiter import LimiterMixin

from natsort import natsorted
import os
from PIL import Image
import numpy as np

# Used in files
import asyncio
from datetime import timedelta
from re import findall
import sys
import json
from shutil import copyfileobj, rmtree, copyfile

async def checkPageExistence (url) :
    with rq.get(url) as r :
        return (r.status_code == 200)
        
async def normalizeInput (input:str) :
    return unicodedata.normalize('NFD', input).encode('ascii', 'ignore').decode('utf-8').lower().replace(' ', '-')

async def create_folder(newpath):
    if not os.path.exists(newpath):
        os.makedirs(newpath)
    return newpath

async def normalizeString(string) :
    return ''.join(c for c in unicodedata.normalize('NFD', string)
                  if unicodedata.category(c) != 'Mn')

class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    """Session class with caching and rate-limiting behavior.
    Accepts keyword arguments for both LimiterSession and CachedSession.
    """

async def link_to_soup(url, session=Session()) :
    with session.get(url) as r :
        if r.status_code == 200 :
            return bs(r.text, features="lxml") 
        else:
            raise ValueError(f'Response code from {url} was not 200 ({r.status_code})')

async def download_file(url, output, file_name, session):
    with session.get(url, stream=True) as r:
        if r.status_code == 200 :
            with open(f'{output}/{file_name}', 'wb') as f:
                copyfileobj(r.raw, f)
        return r.status_code
    
async def retry_function(fun, args=[], max_tries=2):
    for i in range(max_tries):
        try: 
            return await fun(*args)
        except Exception:
            await asyncio.sleep(0.5)
            continue

async def delete_dir(path):
    path_pardir = os.path.abspath(os.path.join(path, os.pardir))
    if len([a for a in os.scandir(path_pardir)]) <= 1:
        await retry_function(rmtree, [path_pardir])
        print(f'Deleted folder "{path_pardir}" (empty)')
    else :
        await retry_function(rmtree, [path])
        print(f'Deleted folder "{path}"')

############################################################

# async def hcomb_folder(dir):
#     subfolders = [f.path for f in os.scandir(dir) if f.is_dir()]

#     if not subfolders:
#         print("No subfolders found in the main folder.\nTrying to use main folder as subfolder.")
#         await hcomb_subfolder(dir)
#     else :
#         asyncio.gather(*[hcomb_subfolder(subfolder) for subfolder in subfolders])

async def hcomb_subfolder(dir, ignore_indexes=[], solo_indexes=[0]):
    data = {}
    sizes = []
    ratios = []
    for (index,a) in enumerate(natsorted([*os.scandir(dir)], key=lambda a: a.name)):
        if index in ignore_indexes:
            continue
        
        width,height = Image.open(a.path).size

        data[a.name.split('.')[0]] = {
            'fp': a.path,
            'w': width,
            'h': height,
            'ratio': width/height,
            'combined': False
        }
        sizes.append((width,height))
        ratios.append(width/height)

    keys = [*data.keys()]

    await create_folder('\\'.join(data[keys[0]]['fp'].split('\\')[0:-1]) + ' - Combined')

    if 0 in solo_indexes :
        (image:=data[keys[0]])['combined'] = True
        copyfile(image['fp'],
                '\\'.join(image['fp'].split('\\')[0:-1]) + f' - Combined\\{keys[0]}.{image['fp'].split('.')[-1]}')
        print(f'Copied "{image['fp'].split('\\')[-1]}"')
    elif data[keys[1]]['ratio'] >= 1:
        (image:=data[keys[0]])['combined'] = True
        copyfile(image['fp'],
                '\\'.join(image['fp'].split('\\')[0:-1]) + f' - Combined\\{keys[0]}.{image['fp'].split('.')[-1]}')
        print(f'Copied "{image['fp'].split('\\')[-1]}"')

    for num in range(1, len((keys))):
        image_before = data[keys[num-1]]
        image = data[keys[num]]
        
        #image solo
        if (num in solo_indexes) or (image_before['combined'] and num == len(keys)-1) or (image['ratio'] >= 1) or (num < len(keys)-1 and not image['combined'] and image_before['combined'] and data[keys[num+1]]['ratio'] >= 1):
            data[keys[num]]['combined'] = True
            copyfile(image['fp'],
                    '\\'.join(image['fp'].split('\\')[0:-1]) + f' - Combined\\{keys[num]}.{image['fp'].split('.')[-1]}')
            print(f'Copied "{image['fp'].split('\\')[-1]}"')

        else:
            if (not image_before['combined'] and not image['combined']) and (image_before['ratio'] < 1 and image['ratio'] < 1):
                data[keys[num-1]]['combined'] = True
                data[keys[num]]['combined'] = True

                await hcomb_imgs(im1_fp=image_before['fp'], im2_fp=image['fp'], 
                                fpath_out='\\'.join(image['fp'].split('\\')[0:-1]) + f' - Combined\\{keys[num-1]}-{keys[num]}.{image['fp'].split('.')[-1]}')

async def hcomb_imgs(im1_fp, im2_fp, fpath_out, right_left=True):
    im1,im2 = (Image.open(im1_fp),Image.open(im2_fp))
    h1,h2 = (im1.size[1], im2.size[1])
    if h1 != h2:
        if h1 > h2:
            im1 = im1.resize([im2.size[0], h2])
        else :
            im2 = im2.resize([im1.size[0], h1])
    Image.fromarray(
        np.concatenate(
            ([arr2:=np.array(im2.convert('RGB')), arr1:=np.array(im1.convert('RGB'))
            ] if right_left else [arr1, arr2])
            ,axis=1
        )).save(fpath_out)
    print(f'Combined "{im1_fp.split('\\')[-1]}" and "{im2_fp.split('\\')[-1]}"')
    # print(f'Combined "{im1_fp.split('\\')[-1]}" and "{im2_fp.split('\\')[-1]}" into "{fpath_out}"')
    return True

###################################################################

async def combine_subfolder(chap_dir : str, output_dir):
    title = chap_dir.split('\\')[-2]
    subfolder_name = os.path.basename(chap_dir)

    image_files = [f for f in os.listdir(chap_dir) if os.path.isfile(os.path.join(chap_dir, f))]
    image_files = natsorted(image_files)

    if not image_files:
        print(f"No images found in the subfolder '{subfolder_name}'.")
        raise ValueError('No images in subfolder')

    first_image = Image.open(os.path.join(chap_dir, image_files[0]))

    other_images = [Image.open(os.path.join(chap_dir, image)).convert('RGB') for image in image_files[1:]]

    output_dir = os.path.join(output_dir, title + " - PDF")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_pdf_path = os.path.join(output_dir, f"{subfolder_name}.pdf")
    first_image.save(output_pdf_path, save_all=True, append_images=other_images)
    print(f"Merged images of '{subfolder_name}' into '{output_pdf_path}'.")
    
    first_image.close()
    for img in other_images:
        img.close()

##################################################################

async def make_pdf_ask(from_dir, pdf_behavior, img_comb, img_del, solo_indexes=[0], ignore_indexes=[]):
    if img_comb :
        await hcomb_subfolder(dir=from_dir, solo_indexes=solo_indexes, ignore_indexes=ignore_indexes)
    if pdf_behavior :
        if img_comb:
            await combine_subfolder(chap_dir=from_dir+' - Combined', output_dir='\\'.join(from_dir.split('\\')[0:-2]))   
            if img_del :
                await delete_dir(from_dir+' - Combined')
        else : #WORKS
            await combine_subfolder(chap_dir=from_dir, output_dir='\\'.join(from_dir.split('\\')[0:-2]))
        if img_del :
            await delete_dir(from_dir)