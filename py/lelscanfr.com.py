from utils import *

async def get_manga_title(soup):
    return findall(r'^.+(?=\r)', soup.find_all("h2", class_="text-2xl font-bold leading-[1.5rem]")[0].text)[0]

async def get_chap_image_link(soup):
    return soup.find_all('img', class_="h-full w-full rounded-lg object-cover object-bottom sm:max-h-[300px] md:max-h-[400px]")[0]['src']

async def get_chap_divs(soup):
    return soup.find_all("div", id="chapters-list")[0].findChildren("a", recursive=False)

async def get_page_num(soup):
    find_all_list = soup.find_all("h3", class_="hidden sm:block")
    if not find_all_list :
        return 1
    return int(findall(r'\d+(?=\r)', find_all_list[0].text)[0])

async def get_chap_links(bs4_elements) :
    links = {} # {Chapter/Volume name : link}

    for a_el in bs4_elements:
        chap_name_span = a_el.findChildren(name="div", attrs={'class' : 'flex gap-2'}, recursive=True)[0].findChildren("span")[0].text
        try :
            chap_name = chap_name_span
        except :
            raise ValueError(f'Failed to extract the chap name from string {repr(chap_name_span)}')
        links[chap_name] = a_el['href']

    return dict(natsorted(links.items()))

async def create_data(link,soup, chap_divs) :
    data = {
        "siteName": "lelscanfr.com",
        "url": link,
        "title": await normalizeString(await get_manga_title(soup)),
        "coverLink": str(await get_chap_image_link(soup)),
        "chaps": {}
    }

    for chap in (links:=(await get_chap_links(chap_divs))).keys():
        data['chaps'][await normalizeString(chap)] = {
            'viewerLink': links[chap]
        }
    return data

async def main () :
    args = sys.argv
    args.pop(0)

    command = args[0]

    if command == 'pageExists' :  
        input = args[1]
        link = f'https://lelscanfr.com/manga/{await normalizeInput(input)}'
        print(await checkPageExistence(link))

    elif command == 'getPageResults' :
        input = args[1]
        link = f'https://lelscanfr.com/manga/{await normalizeInput(input)}'

        with CachedLimiterSession(cache_name='http_cache',per_second=1.5,backend='sqlite',expire_after=timedelta(days=1)) as s :
            soup = await link_to_soup(link,s)
        
            page_num = await get_page_num(soup)
            chap_divs = []
            for x in range(1,page_num+1):
                for div in await get_chap_divs(await link_to_soup(link+f'?page={x}', s)):
                    chap_divs.append(div)

        data = await create_data(link, soup, chap_divs)
        print(data)

    elif command == 'downloadList' : 
        title = args[1]
        toDlList = json.loads(args[2].replace("'", "\""))
        settings = json.loads(args[3].replace("'", "\""))
        
        with CachedLimiterSession(cache_name='http_cache',per_second=1.5,backend='sqlite',expire_after=timedelta(days=1)) as s :
            outputPath = await create_folder(os.path.normpath(os.path.join(os.path.dirname(__file__),'..', settings['outputLocation'])))
            
            for chap in toDlList.keys():
                soup = await link_to_soup(toDlList[chap]['viewerLink'], s)
                chap_imgs = soup.find_all('div', id="chapter-container")[0].findChildren('img')
                imgs_links = [x.attrs['data-src'] for x in chap_imgs]

                chap_path = await create_folder(os.path.join(outputPath, title, chap))
                chap_files = [a.name for a in os.scandir(chap_path)]

                file_ext = imgs_links[0].split('.')[-1]

                counter = 1
                response_status = 200
                print(f'Starting download for {title} {chap}')
                for url in imgs_links:
                    file_name = f'{str(counter)}.{file_ext}'
                    if file_name not in chap_files:
                        response_status = await download_file(url, chap_path, file_name, s)
                        print(f'Response from {url} : {response_status}')
                    else :
                        print(f'Skipping download for {file_name} (already present in folder)')
                    counter += 1
                
                await make_pdf_ask(
                    from_dir=chap_path, 
                    pdf_behavior=(settings['makePdf'] == 'true'), 
                    img_comb=(settings['combineImgs'] == 'true'), 
                    solo_indexes=([int(a) for a in settings['soloIndexes'].split(',')] if settings['soloIndexes']!='' else []),
                    ignore_indexes=([int(a) for a in settings['ignoreIndexes'].split(',')] if settings['ignoreIndexes']!='' else []),
                    img_del=(settings['deleteImgs'] == 'true')
                )

    else :
        quit()

asyncio.run(main())