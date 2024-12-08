const puppeteer = require('puppeteer');
const readline = require('readline');

// Create interface for reading from stdin
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

// Initialize browser
let browser;
let page;

async function initBrowser() {
    browser = await puppeteer.launch({
        headless: "new"
    });
    page = await browser.newPage();
}

async function scrapePremierLeague() {
    try {
        await page.goto('https://www.premierleague.com/results');
        await page.waitForSelector('.matchList');
        
        const results = await page.evaluate(() => {
            const matches = document.querySelectorAll('.matchList .match-fixture');
            return Array.from(matches, match => {
                const homeTeam = match.querySelector('.teams .team:first-child').textContent.trim();
                const awayTeam = match.querySelector('.teams .team:last-child').textContent.trim();
                const score = match.querySelector('.score').textContent.trim();
                const date = match.querySelector('.date').textContent.trim();
                
                return {
                    date,
                    homeTeam,
                    score,
                    awayTeam
                };
            });
        });
        
        return results;
    } catch (error) {
        console.error('Scraping error:', error);
        return { error: error.message };
    }
}

// Send ready message
console.log(JSON.stringify({
    jsonrpc: '2.0',
    method: 'ready',
    id: 'init',
    params: { server: 'puppeteer' }
}));

// Handle incoming messages
rl.on('line', async (line) => {
    try {
        const request = JSON.parse(line);
        
        if (request.method === 'scrape') {
            const results = await scrapePremierLeague();
            
            console.log(JSON.stringify({
                jsonrpc: '2.0',
                id: request.id,
                result: results
            }));
        }
    } catch (error) {
        console.log(JSON.stringify({
            jsonrpc: '2.0',
            id: null,
            error: {
                code: -32000,
                message: error.message
            }
        }));
    }
});

// Initialize browser when starting
initBrowser().catch(console.error);

// Cleanup on exit
process.on('SIGTERM', async () => {
    if (browser) {
        await browser.close();
    }
    process.exit(0);
});
