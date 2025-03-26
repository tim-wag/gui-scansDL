from utils import *

async def get_manga_title(soup):
    return findall(r'.+(?= Scan VF)', soup.find_all("h1", class_="mb-0 d-inline-block h2")[0].text)[0]

async def get_chap_image_link(soup):
    return soup.find_all('div', class_="img-wrapper loading series-picture-lg mx-auto mx-md-0")[0].contents[1]['src']

async def get_chap_links(soup) :
    links = {} # {Chapter/Volume name : link}

    for div in soup.find_all("div", class_="col-12 col-lg-6 py-3 col-chapter"):
        a_child = div.findChildren("a", recursive=False)[0]
        chap_name_div = a_child.findChildren(name="h5", attrs={'class' : 'mb-0'}, recursive=True)[0].text
        try :
            chap_name = findall(r'(?<=\s|\n)\w.+(?=\n\s*\d)', chap_name_div)[0]
        except :
            raise ValueError(f'Failed to extract the chap name from string {repr(chap_name_div)}')
        links[chap_name] = "https://scanvf.org"+a_child['href']

    return dict(natsorted(links.items()))

async def create_data(link,soup) :
    data = {
        "siteName": "scanvf.org",
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

async def get_cdn_link(chap_url, session):
    soupChap = await link_to_soup(chap_url, session)
    scan_img = soupChap.find_all("img", class_="img-fluid")[1]
    
    cdn_link = findall(r'.+(?=\?)', scan_img['src'])[0]

    # Returns the link to the first image of the scan
    return cdn_link

async def main () :
    args = sys.argv
    args.pop(0)

    command = args[0]

    if command == 'pageExists' :  
        input = args[1]
        link = f'https://scanvf.org/manga/{await normalizeInput(input)}'
        print(await checkPageExistence(link))

    elif command == 'getPageResults' :
        input = args[1]
        link = f'https://scanvf.org/manga/{await normalizeInput(input)}'


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
                cdn_link = await get_cdn_link(toDlList[chap]['viewerLink'], s)
                base_url = findall(r'^.+(?=/.+$)', cdn_link)[0]
                file_ext = cdn_link.split('.')[-1]
                chap_path = await create_folder(os.path.join(outputPath, title, chap))
                chap_files = [a.name for a in os.scandir(chap_path)]
                
                counter = 1
                response_status = 200
                print(f'Starting download for {title} {chap}')
                while response_status == 200:
                    # The file extension changes depending on the website
                    file_name = f'{counter}.{file_ext}'
                    url = f'{base_url}/{file_name}'
                    if file_name not in chap_files :
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