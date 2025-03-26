const { shell, ipcRenderer } = require('electron')
//const he = require('he')

const searchField = document.getElementById("search-input")
const sitesList = document.getElementById('sites-list')
const siteHeader = document.getElementById('site-header')
const mangaHeader = document.getElementById('manga-header')
const mangaCover = document.getElementById('manga-cover')
const downloadList = document.getElementById('download-list')
const downloadButton = document.getElementById('download-button')
const console = document.getElementById('console-wrapper')
const settingsSection = document.getElementById('settings-section')
const imgCombineForm = document.getElementById('img-combine')

let selected_chap_list = []
let data = {}
let settings = {}
let scraper = ''
let title = ''
let chaptersDL = {}

document.addEventListener('DOMContentLoaded', () => {
    ipcRenderer.send('getScraperList');
})

imgCombineForm.onchange = function () {
    if (imgCombineForm.elements['img-combine'].value !== 'true') {
        document.getElementById('soloindexes-div').toggleAttribute('hidden')
        document.getElementById('ignoreindexes-div').toggleAttribute('hidden')
    } else {
        document.getElementById('soloindexes-div').removeAttribute('hidden')
        document.getElementById('ignoreindexes-div').removeAttribute('hidden')
    }
}

downloadButton.onclick = function () {
    settingsSection.removeAttribute('hidden')
};

document.getElementById('cancel-settings').onclick = function () {
    settingsSection.toggleAttribute('hidden')
};

document.getElementById('ok-settings-btn').onclick = function () {
    selected_chap_list = []
    for (var i = 0; i < downloadList.selectedOptions.length; i++) {
        selected_chap_list.push(downloadList.selectedOptions[i].value)
    }
    scraper = `${data.siteName}.py`
    title = data.title
    chaptersDL = {}
    selected_chap_list.forEach (chap => {
        chaptersDL[chap] = data['chaps'][chap]
    })

    const outputLocation = document.getElementById('output-location').value
    const combineImgs = imgCombineForm.elements['img-combine'].value
    const soloIndexes = document.getElementById('solo-indexes').value
    const ignoreIndexes = document.getElementById('ignore-indexes').value
    const makePdf = document.getElementById('make-pdf').elements['make-pdf'].value
    const deleteImgs = document.getElementById('delete-imgs').elements['delete-imgs'].value

    settings = {}
    settings = {
        "outputLocation": outputLocation,
        "combineImgs": combineImgs,
        "soloIndexes": soloIndexes,
        "ignoreIndexes": ignoreIndexes,
        "makePdf": makePdf,
        "deleteImgs": deleteImgs
    }
    settingsSection.toggleAttribute('hidden')
    ipcRenderer.send('downloadList', scraper, title, chaptersDL, settings)
}

ipcRenderer.on('scraperList', (e, list) => {
    list.forEach(site => {
        var li = document.createElement('li');
        li.appendChild(document.createTextNode(site.replace('.py', '')));
        sitesList.appendChild(li)
    })
})

searchField.addEventListener('keyup', (e) => {
    if (e.key === "Enter") {
        resultsList = []
        sitesList.textContent = ''
        ipcRenderer.send('search-input', searchField.value)
    }
})

ipcRenderer.on('scraperHasPage', (e, [scraper, search]) => {
    var li = document.createElement('li')
    li.appendChild(document.createTextNode(scraper.replace('.py', '')))
    li.classList.add('pointer')
    li.onclick = function () {
        ipcRenderer.send('page-clicked', scraper, search)
    }
    sitesList.appendChild(li)
})

function checkDLButtonDisplay() {
    const optionLength = downloadList.selectedOptions.length
    document.getElementById('selected-counter').textContent = String(optionLength)
    if (optionLength === 0) {
        downloadButton.toggleAttribute('hidden')
    } else {
        downloadButton.removeAttribute('hidden')
    }
}

ipcRenderer.on('pageResults', (e, json) => {
    data = json
    downloadList.innerHTML = ('')

    siteHeader.children[0].innerText = json.siteName
    siteHeader.children[0].onclick = function () {shell.openExternal(`https://${json.siteName}`)}
    siteHeader.children[0].classList.add('pointer')
    
    siteHeader.children[1].innerText = json.url
    siteHeader.children[1].onclick = function () {shell.openExternal(json.url)}
    siteHeader.children[1].classList.add('pointer')
    
    mangaHeader.children[0].innerText = json.title
    mangaCover.src = json.coverLink
    checkDLButtonDisplay()

    for (chap in json.chaps) {
        var opt = document.createElement('option')
        opt.innerText = chap
        opt.value = chap
        opt.onclick = function () {checkDLButtonDisplay()}
        downloadList.appendChild(opt)
    }

    document.getElementById('site-info-wrapper').removeAttribute('hidden')
})

ipcRenderer.on('console-output', (e, message) => {
    while (console.children.length >= 250) {
        console.removeChild(console.firstChild)
    }
    var p = document.createElement('p')
    p.textContent = message
    console.appendChild(p)
    console.scrollTop = console.scrollHeight
    // messages.forEach (message => {
    //     var p = document.createElement('p')
    //     p.textContent = message
    //     console.appendChild(p)
    // })
})