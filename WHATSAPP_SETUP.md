# WhatsApp setup

Your report sends a **PNG image** to WhatsApp **groups** (`...@g.us`). Pick one provider:

## Green API

Regular updates are sent as a PNG with no caption to the primary group.
Special slots are sent as PNGs with bold captions to both configured groups.

1. In `config.yaml`: `provider: "green_api"`
2. In `.env`:

```env
WHATSAPP_PROVIDER=green_api
GREEN_API_URL=https://7107.api.greenapi.com
GREEN_API_INSTANCE_ID=7107659529
GREEN_API_TOKEN=your_green_api_token
WHATSAPP_TO=120363028290712457@g.us
WHATSAPP_TO_LUNCH_EOD=120363028290712457@g.us,120363146984037888@g.us
```

3. Test:

```cmd
.venv\Scripts\python.exe main.py --once --force
```

## Evolution API

Also supports groups, images, and captions if you use an Evolution API server.

```env
WHATSAPP_PROVIDER=evolution
EVOLUTION_API_URL=https://your-server.com
EVOLUTION_API_KEY=your_api_key
EVOLUTION_INSTANCE=your_instance_name
WHATSAPP_TO=120363028290712457@g.us
WHATSAPP_TO_LUNCH_EOD=120363028290712457@g.us,120363146984037888@g.us
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
- `caption` — e.g. empty for regular updates or `*Tea_Time*`
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
