const { Client } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

// bikin client WhatsApp
const client = new Client();

client.on('qr', qr => {
    console.log('SCAN QR INI:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('BOT READY ✔️');
});

// MESSAGE HANDLER
client.on('message', async (msg) => {
    if (msg.fromMe) return;

    console.log("📩 MASUK DARI WA:", msg.body);

    try {
        const res = await axios.post('http://127.0.0.1:8000/chat', {
            message: msg.body
        });

        console.log("📤 RESPON API:", res.data);

        await msg.reply(res.data.reply);

    } catch (err) {
        console.log("❌ ERROR:", err.message);
        await msg.reply("Server error 😢");
    }
});

// start bot
client.initialize();