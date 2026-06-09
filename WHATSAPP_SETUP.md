# WhatsApp setup (replace Green API)

Your report sends a **PNG image** to WhatsApp **groups** (`...@g.us`). Pick one provider:

## Recommended: Evolution API

Works like Green API: groups, images, captions. You need an Evolution API server (self-hosted or from your IT vendor).

1. In `config.yaml`: `provider: "evolution"`
2. In `.env`:

```env
WHATSAPP_PROVIDER=evolution
EVOLUTION_API_URL=https://your-server.com
EVOLUTION_API_KEY=your_api_key
EVOLUTION_INSTANCE=your_instance_name
WHATSAPP_TO=120363043968066561@g.us
WHATSAPP_TO_LUNCH_EOD=120363028290712457@g.us,120363146984037888@g.us
```

3. Test:

```cmd
.venv\Scripts\python.exe main.py --once --force
```

## Twilio WhatsApp

Official, paid. Good for single numbers; **group + image** needs extra Twilio media configuration.

```env
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+1...
WHATSAPP_TO=whatsapp:+27...
```

## Custom webhook

If your company has a small service that posts to WhatsApp, point the app at it.

```env
WHATSAPP_PROVIDER=webhook
WHATSAPP_WEBHOOK_URL=https://your-bridge/send
```

**POST with image** (multipart):

- `chatId` — e.g. `120363043968066561@g.us`
- `caption` — e.g. `14:00` or `*EOD*`
- `image` — PNG file

**POST text only** (JSON):

```json
{"chatId": "120363...@g.us", "message": "...", "caption": "..."}
```

## Preview without sending

```env
WHATSAPP_PROVIDER=console
```

```cmd
.venv\Scripts\python.exe main.py --once --dry-run --force
```
