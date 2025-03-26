from utils import *

async def get_manga_title(soup):
    return soup.find_all("h1", class_="entry-title")[0].text

async def get_chap_image_link(soup):
    return soup.find_all('img', class_="attachment- size- wp-post-image")[0]['data-src']

async def get_chap_links(soup) :
    links = {} # {Chapter/Volume name : link}

    for li in soup.find("div", id="chapterlist").findChildren(name='ul')[0].contents:
        a_child = li.findChildren("a", recursive=True)[0]
        chap_name = a_child.findChildren(name="span", attrs={'class' : 'chapternum'}, recursive=False)[0].text
        links[chap_name] = a_child['href']

    return dict(natsorted(links.items()))

async def create_data(link,soup) :
    data = {
        "siteName": "japscans.fr",
        "url": link,
        "title": await normalizeString(await get_manga_title(soup)),
        "coverLink": str(await get_chap_image_link(soup)),
        "chaps": {}
    }
    for chap in (links:=(await get_chap_links(soup))).keys():
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
        link = f'https://japscans.fr/manga/{await normalizeInput(input)}'
        print(await checkPageExistence(link))

    elif command == 'getPageResults' :
        input = args[1]
        link = f'https://japscans.fr/manga/{await normalizeInput(input)}'

        soup = await link_to_soup(link)

        data = await create_data(link, soup)
        print(data)

    elif command == 'downloadList' : 
        title = args[1]
        toDlList = json.loads(args[2].replace("'", "\""))
        settings = json.loads(args[3].replace("'", "\""))
        
        with CachedLimiterSession(cache_name='http_cache',per_second=1.5,backend='sqlite',expire_after=timedelta(days=1)) as s :
            outputPath = await create_folder(os.path.normpath(os.path.join(os.path.dirname(__file__),'..', settings['outputLocation'])))
            
            for chap in toDlList.keys():
                soupChap = await link_to_soup(toDlList[chap]['viewerLink'], s)
                imgs = soupChap.find('div', id="readerarea").findChildren('img', recursive=True)

                chap_path = await create_folder(os.path.join(outputPath, title, chap))
                chap_files = [a.name for a in os.scandir(chap_path)]
                
                print(f'Starting download for {title} {chap}')
                for img in imgs :
                    link = img['data-src']
                    file_name = link.split('/')[-1]
                    if file_name not in chap_files :
                        response_status = await download_file(link, chap_path, file_name, s)
                        print(f'Response from {link} : {response_status}')
                    else :
                        print(f'Skipping download for {file_name} (already present in folder)')

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