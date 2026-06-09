from __future__ import annotations

import os
from typing import Optional

import requests


class WhatsAppSender:
    def send(self, message: str) -> None:
        raise NotImplementedError


class CallMeBotSender(WhatsAppSender):
    def __init__(self, phone: str, api_key: str) -> None:
        self.phone = phone
        self.api_key = api_key

    def send(self, message: str) -> None:
        url = "https://api.callmebot.com/whatsapp.php"
        response = requests.get(
            url,
            params={"phone": self.phone, "text": message, "apikey": self.api_key},
            timeout=30,
        )
        response.raise_for_status()


class MetaCloudSender(WhatsAppSender):
    def __init__(self, token: str, phone_number_id: str, group_id: str) -> None:
        self.token = token
        self.phone_number_id = phone_number_id
        self.group_id = group_id

    def send(self, message: str) -> None:
        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": self.group_id,
            "type": "text",
            "text": {"body": message[:4096]},
        }
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30,
        )
        response.raise_for_status()


class TwilioSender(WhatsAppSender):
    def __init__(self, account_sid: str, auth_token: str, from_num: str, to: str) -> None:
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_num = from_num
        self.to = to

    def send(self, message: str) -> None:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        response = requests.post(
            url,
            data={"From": self.from_num, "To": self.to, "Body": message[:1600]},
            auth=(self.account_sid, self.auth_token),
            timeout=30,
        )
        response.raise_for_status()


class WebhookSender(WhatsAppSender):
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send(self, message: str) -> None:
        response = requests.post(
            self.webhook_url,
            json={"message": message},
            timeout=30,
        )
        response.raise_for_status()


class GreenApiSender(WhatsAppSender):
    """https://green-api.com/en/docs/api/sending/SendMessage/"""

    def __init__(self, api_url: str, instance_id: str, api_token: str, chat_id: str) -> None:
        base = api_url.rstrip("/")
        self.url = f"{base}/waInstance{instance_id}/sendMessage/{api_token}"
        self.chat_id = chat_id

    def send(self, message: str) -> None:
        payload = {"chatId": self.chat_id, "message": message[:20000]}
        response = requests.post(
            self.url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and data.get("idMessage") is None and data.get("message"):
            raise RuntimeError(f"Green API error: {data}")


def get_whatsapp_sender() -> Optional[WhatsAppSender]:
    provider = os.getenv("WHATSAPP_PROVIDER", "").lower().strip()

    if provider == "greenapi":
        api_url = os.getenv("GREENAPI_URL", "https://api.green-api.com")
        instance = os.getenv("GREENAPI_ID_INSTANCE", "")
        token = os.getenv("GREENAPI_API_TOKEN", "")
        chat_id = os.getenv("GREENAPI_CHAT_ID", "")
        if instance and token and chat_id:
            return GreenApiSender(api_url, instance, token, chat_id)

    if provider == "callmebot":
        phone = os.getenv("CALLMEBOT_PHONE", "")
        apikey = os.getenv("CALLMEBOT_APIKEY", "")
        if phone and apikey:
            return CallMeBotSender(phone, apikey)

    if provider == "meta":
        token = os.getenv("WHATSAPP_TOKEN", "")
        phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        group = os.getenv("WHATSAPP_GROUP_ID", "")
        if token and phone_id and group:
            return MetaCloudSender(token, phone_id, group)

    if provider == "twilio":
        sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        token = os.getenv("TWILIO_AUTH_TOKEN", "")
        from_num = os.getenv("TWILIO_WHATSAPP_FROM", "")
        to = os.getenv("TWILIO_WHATSAPP_TO", "")
        if sid and token and from_num and to:
            return TwilioSender(sid, token, from_num, to)

    webhook = os.getenv("WHATSAPP_WEBHOOK_URL", "")
    if webhook:
        return WebhookSender(webhook)

    return None
