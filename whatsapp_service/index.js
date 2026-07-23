const express = require('express');
const makeWASocket = require('@whiskeysockets/baileys').default;
const { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode');
const axios = require('axios');
const path = require('path');
const fs = require('fs');
const pino = require('pino');

const logger = pino({ level: 'info' });
const app = express();
const PORT = process.env.PORT || 3000;
const ODOO_WEBHOOK_URL = process.env.ODOO_WEBHOOK_URL || 'http://odoo:8069/api/whatsapp/webhook';
const SESSION_DIR = path.join(__dirname, 'session');

app.use(express.json());

let sock = null;
let currentQr = null;
let connectionStatus = 'disconnected'; // 'disconnected' | 'connecting' | 'connected'
let retryCount = 0;

// Ensure session directory exists
if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
}

async function connectToWhatsApp() {
    try {
        const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
        
        connectionStatus = 'connecting';
        logger.info('Fetching latest Baileys version...');
        
        let version = [2, 3000, 1015920080];
        try {
            const result = await fetchLatestBaileysVersion();
            version = result.version;
            logger.info(`Fetched latest Baileys version: ${version.join('.')}`);
        } catch (err) {
            logger.warn(`Failed to fetch latest Baileys version, using fallback [${version.join('.')}] due to: ${err.message}`);
        }

        logger.info('Initializing Baileys WASocket...');

        sock = makeWASocket({
            version,
            auth: state,
            printQRInTerminal: true,
            browser: ['DeployGuard', 'Chrome', '120.0.0'],
            logger: pino({ level: 'silent' }) // Silence noisy internal Baileys logging
        });
        
        sock.ev.on('creds.update', saveCreds);
        
        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            if (qr) {
                currentQr = qr;
                connectionStatus = 'connecting';
                logger.info('New QR code received, scan to link device.');
            }
            
            if (connection === 'open') {
                connectionStatus = 'connected';
                currentQr = null;
                retryCount = 0;
                logger.info('WhatsApp connection successfully opened!');
            }
            
            if (connection === 'close') {
                currentQr = null;
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                
                logger.warn(`Connection closed. StatusCode: ${statusCode}, Reconnecting: ${shouldReconnect}`);
                connectionStatus = 'disconnected';
                
                if (shouldReconnect) {
                    // Reset exponential backoff if the disconnect is due to QR code timing out (408) or standard QR rotation
                    if (statusCode === 408 || statusCode === DisconnectReason.timedOut || !sock?.user) {
                        logger.info('QR code timed out or rotated without scan. Reconnecting immediately for a fresh QR...');
                        retryCount = 0;
                    } else {
                        retryCount++;
                    }
                    const delay = Math.min(1000 * Math.pow(2, retryCount), 10000); // Back off up to 10s max
                    logger.info(`Attempting reconnect in ${delay / 1000}s...`);
                    setTimeout(connectToWhatsApp, delay);
                } else {
                    logger.error('Logged out of WhatsApp. Clearing session store and restarting scanner...');
                    try {
                        fs.rmSync(SESSION_DIR, { recursive: true, force: true });
                        fs.mkdirSync(SESSION_DIR, { recursive: true });
                    } catch (err) {
                        logger.error('Error clearing session dir:', err.message);
                    }
                    retryCount = 0;
                    setTimeout(connectToWhatsApp, 1000);
                }
            }
        });
        
        sock.ev.on('messages.upsert', async (m) => {
            if (m.type !== 'notify') return;
            
            for (const msg of m.messages) {
                if (msg.key.fromMe) continue; // Ignore messages from ourselves
                
                const sender = msg.key.remoteJid;

                // Recursive helper to extract text from complex/nested Baileys message structures
                const extractText = (mMsg) => {
                    if (!mMsg) return null;
                    return mMsg.conversation || 
                           mMsg.extendedTextMessage?.text || 
                           mMsg.imageMessage?.caption || 
                           mMsg.videoMessage?.caption || 
                           mMsg.documentMessage?.caption || 
                           mMsg.buttonsResponseMessage?.selectedButtonId || 
                           mMsg.listResponseMessage?.singleSelectReply?.selectedRowId || 
                           mMsg.templateButtonReplyMessage?.selectedId || 
                           extractText(mMsg.ephemeralMessage?.message) || 
                           extractText(mMsg.viewOnceMessage?.message) || 
                           extractText(mMsg.viewOnceMessageV2?.message) || 
                           extractText(mMsg.documentWithCaptionMessage?.message) || 
                           extractText(mMsg.editedMessage?.message?.protocolMessage?.editedMessage) || 
                           null;
                };

                const text = extractText(msg.message);
                
                if (!text || typeof text !== 'string' || text.trim() === '') {
                    logger.warn(`Received message from [${sender}] without extractable text payload.`);
                    continue;
                }
                
                logger.info(`Received WhatsApp message from [${sender}]: "${text}"`);
                
                try {
                    // Forward message payload to Odoo's JSON-RPC webhook
                    const response = await axios.post(ODOO_WEBHOOK_URL, {
                        jsonrpc: "2.0",
                        method: "call",
                        params: {
                            From: sender,
                            Body: text
                        }
                    }, {
                        headers: { 'Content-Type': 'application/json' },
                        timeout: 15000
                    });
                    
                    const result = response.data?.result;
                    if (result && result.reply) {
                        // Calculate variable human response delay between 15 and 30 seconds
                        const delayMs = Math.floor(Math.random() * (30000 - 15000 + 1)) + 15000;
                        const delaySec = (delayMs / 1000).toFixed(1);
                        logger.info(`Simulating human response delay for [${sender}]: waiting ${delaySec}s before sending reply...`);

                        // Display 'typing...' status on recipient's WhatsApp UI during the delay
                        try { await sock.sendPresenceUpdate('composing', sender); } catch (e) {}

                        setTimeout(async () => {
                            try {
                                await sock.sendPresenceUpdate('paused', sender);
                                logger.info(`Sending delayed WhatsApp response to [${sender}]`);
                                await sock.sendMessage(sender, { text: result.reply });
                            } catch (err) {
                                logger.error(`Error sending delayed WhatsApp reply to [${sender}]:`, err.message);
                            }
                        }, delayMs);
                    } else if (response.data?.error) {
                        logger.error('Odoo JSON-RPC returned an error:', response.data.error);
                    }
                } catch (error) {
                    logger.error(`Odoo Webhook error for message from [${sender}]:`, error.message);
                }
            }
        });
    } catch (err) {
        logger.error('Fatal socket connection error:', err.message);
        setTimeout(connectToWhatsApp, 10000);
    }
}

// REST Endpoints
app.post('/restart', async (req, res) => {
    logger.info('Restart requested via REST API. Reconnecting socket (session credentials preserved)...');
    try {
        currentQr = null;
        connectionStatus = 'connecting';
        retryCount = 0;
        if (sock) {
            try { sock.ws.close(); } catch (e) {}
            sock = null;
        }
        // Only remove session if force=true is passed; default keeps creds.json intact
        if (req.body?.force === true && fs.existsSync(SESSION_DIR)) {
            logger.warn('Force parameter received. Clearing session directory...');
            fs.rmSync(SESSION_DIR, { recursive: true, force: true });
            fs.mkdirSync(SESSION_DIR, { recursive: true });
        }
        setTimeout(connectToWhatsApp, 500);
        res.json({ status: 'restarting' });
    } catch (err) {
        logger.error('Error during restart:', err.message);
        res.status(500).json({ error: err.message });
    }
});

app.get('/status', (req, res) => {
    res.json({
        status: connectionStatus,
        hasQr: !!currentQr
    });
});

app.get('/qr', async (req, res) => {
    if (connectionStatus === 'connected') {
        res.type('image/svg+xml').send(`
            <svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
                <rect width="100%" height="100%" fill="#ffffff" rx="12" stroke="#e1e4e6" stroke-width="2"/>
                <circle cx="150" cy="115" r="45" fill="#e8f5e9"/>
                <circle cx="150" cy="115" r="35" fill="#25D366"/>
                <path d="M142 115 l6 6 l12 -12" stroke="white" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                <text x="150" y="195" font-family="system-ui, -apple-system, sans-serif" font-size="18" font-weight="700" fill="#25D366" text-anchor="middle">LINKED</text>
                <text x="150" y="225" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="500" fill="#1c1e21" text-anchor="middle">WhatsApp Bridge Active</text>
                <text x="150" y="248" font-family="system-ui, -apple-system, sans-serif" font-size="12" fill="#8d949e" text-anchor="middle">DeployGuard AI is online</text>
            </svg>
        `);
        return;
    }

    if (connectionStatus === 'connecting' && !currentQr) {
        res.type('image/svg+xml').send(`
            <svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
                <rect width="100%" height="100%" fill="#ffffff" rx="12" stroke="#e1e4e6" stroke-width="2"/>
                <circle cx="150" cy="115" r="35" fill="none" stroke="#25D366" stroke-width="5" stroke-linecap="round" stroke-dasharray="140 40">
                    <animateTransform attributeName="transform" type="rotate" from="0 150 115" to="360 150 115" dur="1.5s" repeatCount="indefinite"/>
                </circle>
                <text x="150" y="195" font-family="system-ui, -apple-system, sans-serif" font-size="18" font-weight="700" fill="#1c1e21" text-anchor="middle">INITIALIZING</text>
                <text x="150" y="225" font-family="system-ui, -apple-system, sans-serif" font-size="13" fill="#606770" text-anchor="middle">Preparing session socket...</text>
            </svg>
        `);
        return;
    }

    if (!currentQr) {
        res.type('image/svg+xml').send(`
            <svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
                <rect width="100%" height="100%" fill="#ffffff" rx="12" stroke="#e1e4e6" stroke-width="2"/>
                <circle cx="150" cy="115" r="45" fill="#ffebee"/>
                <path d="M135 100 l30 30 M165 100 l-30 30" stroke="#f44336" stroke-width="5" stroke-linecap="round"/>
                <text x="150" y="195" font-family="system-ui, -apple-system, sans-serif" font-size="18" font-weight="700" fill="#f44336" text-anchor="middle">DISCONNECTED</text>
                <text x="150" y="225" font-family="system-ui, -apple-system, sans-serif" font-size="13" fill="#606770" text-anchor="middle">Could not acquire QR string</text>
            </svg>
        `);
        return;
    }

    try {
        // Generate QR code PNG stream directly
        res.setHeader('Content-Type', 'image/png');
        await qrcode.toFileStream(res, currentQr, {
            width: 300,
            margin: 2,
            color: {
                dark: '#1c1e21',
                light: '#ffffff'
            }
        });
    } catch (err) {
        logger.error('Error streaming QR code:', err.message);
        res.status(500).send('Error generating QR code');
    }
});

// Trigger connection loop
connectToWhatsApp();

app.listen(PORT, '0.0.0.0', () => {
    logger.info(`DeployGuard WhatsApp Bridge Service listening on port ${PORT}`);
});
