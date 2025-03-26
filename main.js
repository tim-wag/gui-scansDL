const { app, BrowserWindow, ipcMain, Menu } = require('electron')
const path = require('node:path')
const { PythonShell } = require('python-shell')
const fs = require('fs')

// var server = require('http').createServer()
// var io = require('socket.io')(server)
// io.on('connection', function () {
//     console.log('connected')
// })
// server.listen(3000)

const pyDir = path.join(__dirname, 'py')

PythonShell.defaultOptions = {
    scriptPath: './py',
    mode: 'text'
};

/////////////////
// WINDOW LOGIC
/////////////////

var sendConsole = () => {}

const createWindow = () => {
    const win = new BrowserWindow({
        width: 1000,
        height: 600,
        webPreferences : {
            //preload: path.join(__dirname, "preload.js"),
            nodeIntegration: true,
            contextIsolation: false,
        },
    })

    sendConsole = (output) => {
        console.log(output)
        win.webContents.send('console-output', output)
    }

    const menu = Menu.buildFromTemplate([
        {
          label: 'Settings',
          click: () => console.log('settings'),
        //   submenu: [
        //     {
        //       //click: () => win.webContents.send('update-counter', 1),
        //       label: 'set1'
        //     },
        //     {
        //       //click: () => win.webContents.send('update-counter', -1),
        //       label: 'set2'
        //     }
        //  ]
        },
        {
            label: 'DevTools',
            click: () => {win.webContents.openDevTools()}
        }
      ])
    Menu.setApplicationMenu(menu)

    win.loadFile("index.html")
}
app.whenReady().then(() => {
    createWindow()
})
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit()
})

/////////////////
// APP AND PYTHON
/////////////////

function getPyScrapers() {
    const scrapers = []

    fs.readdirSync(pyDir).forEach(file => {
        if (file.match(/\S+\.\S+\.py$/)) {
            scrapers.push(file)
        }
    })
    return scrapers
}
const scraperList = getPyScrapers() //OK

async function pageExists(file, input) {
    try {
        return ((await PythonShell
        .run(file, {
            args: ['pageExists', input]
        }))
            [0].toLowerCase() === 'true')
    } catch (err) {
        return 'errror '+err
    }
}

async function getPageResults(scraper, input) {
    try {
        return (await PythonShell
            .run(scraper, { args: ['getPageResults', input] })
        )
    } catch (err) {
        console.log('getPageResults error')
        sendConsole(`error parsing for ${input}`)
    }
}

async function downloadList (scraper, title, list, settings) {
    new PythonShell(scraper, { args: [
        'downloadList', title, JSON.stringify(list), JSON.stringify(settings)
    ] })
    .on('message', function (message) {
        sendConsole(message)
    })
}

ipcMain.on('getScraperList', (e) => {
    e.sender.send('scraperList', scraperList)
})

ipcMain.on('search-input', (e, search) => {
    scraperList.forEach(scraper => {
        (async () => {
            try {
                if (await pageExists(scraper, search)) {
                    sendConsole(`${scraper.split('.').slice(0,-1).join('.')} has page`)
                    e.sender.send('scraperHasPage', [scraper, search])
                } else {
                    sendConsole(`${scraper.split('.').slice(0,-1).join('.')} hasn't page`)
                }
            } catch (err) {
                console.log('scraperHasPage error :', err)
            }
        })()
    })
})

ipcMain.on('page-clicked', (e, scraper, input) => {
    (async () => {
        try {
            e.sender.send('pageResults', JSON.parse((await getPageResults(scraper, input))[0].replaceAll(`'`, `"`)))
        } catch (err) {
            console.log('pageResults error: ', err)
        }
    })()
})

ipcMain.on('downloadList', (e, scraper, title, chaptersList, settings) => {
    (async () => {
        try {
            await downloadList(scraper, title, chaptersList, settings)
        } catch (err) {
            console.log('downloadList error :', err)
        }
    })()
})