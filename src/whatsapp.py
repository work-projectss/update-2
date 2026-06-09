from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

from datetime import datetime

import requests

from src.config_loader import AppConfig
from src.schedule_rules import uses_dual_groups

log = logging.getLogger("alpha1-update")


def _env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _evolution_number(chat_id: str) -> str:
    """Evolution API accepts group JID or E.164 number."""
    return chat_id.strip()


class WhatsAppSender:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._provider = config.whatsapp_provider.lower()
        self._send_as_image = config.whatsapp_send_as_image

    def _chat_ids_for_caption(
        self, caption: str, *, at: datetime | None = None
    ) -> list[str]:
        if uses_dual_groups(caption):
            if self._config.whatsapp_lunch_eod_chats:
                return list(self._config.whatsapp_lunch_eod_chats)
            raise ValueError(
                "Set WHATSAPP_TO_LUNCH_EOD in .env or "
                "whatsapp.dual_groups in config.yaml"
            )
        if self._config.whatsapp_default_chat:
            return [self._config.whatsapp_default_chat]
        raise ValueError(
            "Set WHATSAPP_TO in .env or whatsapp.default_group in config.yaml"
        )

    def send(
        self,
        message: str,
        *,
        image_path: Path | None = None,
        at: datetime | None = None,
    ) -> None:
        chat_ids = self._chat_ids_for_caption(message, at=at)
        for chat_id in chat_ids:
            self._send_to_chat(chat_id, message, image_path=image_path)

    def _send_to_chat(
        self, chat_id: str, message: str, *, image_path: Path | None = None
    ) -> None:
        if image_path and self._send_as_image:
            self._send_image(chat_id, image_path, message)
            return
        if self._provider == "console":
            print(f"[{chat_id}] {message}")
            if image_path:
                print(f"  Image: {image_path}")
            return
        if self._provider == "twilio":
            self._send_twilio_text(chat_id, message)
            return
        if self._provider == "green_api":
            self._send_green_api_text(chat_id, message)
            return
        if self._provider == "evolution":
            self._send_evolution_text(chat_id, message)
            return
        if self._provider == "webhook":
            self._send_webhook_text(chat_id, message)
            return
        raise ValueError(
            f"Unknown whatsapp provider: {self._provider}. "
            "Use evolution, twilio, webhook, or console in config.yaml"
        )

    def _send_image(self, chat_id: str, image_path: Path, caption: str) -> None:
        if self._provider == "console":
            print(f"[{chat_id}] {caption}")
            print(f"  Image: {image_path.resolve()}")
            return
        if self._provider == "green_api":
            self._send_green_api_file(chat_id, image_path, caption)
            return
        if self._provider == "evolution":
            self._send_evolution_image(chat_id, image_path, caption)
            return
        if self._provider == "webhook":
            self._send_webhook_file(chat_id, image_path, caption)
            return
        if self._provider == "twilio":
            self._send_twilio_text(
                chat_id,
                f"{caption}\n\n(Image: {image_path.name} — Twilio needs media URL; use evolution or webhook for PNG)",
            )
            return
        raise ValueError(f"Unknown whatsapp provider: {self._provider}")

    # --- Twilio ---
    def _send_twilio_text(self, chat_id: str, message: str) -> None:
        sid = os.environ["TWILIO_ACCOUNT_SID"]
        token = os.environ["TWILIO_AUTH_TOKEN"]
        from_num = os.environ["TWILIO_WHATSAPP_FROM"]
        to_num = chat_id if chat_id.startswith("whatsapp:") else f"whatsapp:{chat_id}"
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        response = requests.post(
            url,
            auth=(sid, token),
            data={"From": from_num, "To": to_num, "Body": message},
            timeout=30,
        )
        response.raise_for_status()
        log.info("Twilio message sent to %s", to_num)

    # --- Green API (legacy) ---
    def _green_api_base(self) -> tuple[str, str]:
        instance = _env("GREEN_API_INSTANCE_ID", "GREENAPI_ID_INSTANCE")
        token = _env("GREEN_API_TOKEN", "GREENAPI_API_TOKEN")
        if not instance or not token:
            raise ValueError(
                "Set GREEN_API_INSTANCE_ID and GREEN_API_TOKEN (or GREENAPI_* in .env)"
            )
        return instance, token

    def _send_green_api_text(self, chat_id: str, message: str) -> None:
        instance, token = self._green_api_base()
        url = (
            f"https://api.green-api.com/waInstance{instance}"
            f"/sendMessage/{token}"
        )
        response = requests.post(
            url,
            json={"chatId": chat_id, "message": message},
            timeout=30,
        )
        response.raise_for_status()
        log.info("Green API message sent to %s", chat_id)

    def _send_green_api_file(self, chat_id: str, image_path: Path, caption: str) -> None:
        instance, token = self._green_api_base()
        url = (
            f"https://api.green-api.com/waInstance{instance}"
            f"/sendFileByUpload/{token}"
        )
        with image_path.open("rb") as handle:
            response = requests.post(
                url,
                data={"chatId": chat_id, "caption": caption[:1024]},
                files={"file": (image_path.name, handle, "image/png")},
                timeout=60,
            )
        if not response.ok:
            raise RuntimeError(
                f"Green API {response.status_code} — chatId={chat_id!r} — {response.text[:400]}"
            )
        log.info(
            "Green API image sent to %s (caption: %s)",
            chat_id,
            caption if caption else "(none)",
        )

    # --- Evolution API (recommended replacement; supports groups @g.us) ---
    def _evolution_base(self) -> tuple[str, str, str]:
        base = _env("EVOLUTION_API_URL", "EVOLUTION_BASE_URL").rstrip("/")
        api_key = _env("EVOLUTION_API_KEY", "EVOLUTION_API_TOKEN")
        instance = _env("EVOLUTION_INSTANCE", "EVOLUTION_INSTANCE_NAME")
        if not base or not api_key or not instance:
            raise ValueError(
                "Set EVOLUTION_API_URL, EVOLUTION_API_KEY, and EVOLUTION_INSTANCE in .env"
            )
        return base, api_key, instance

    def _evolution_headers(self, api_key: str) -> dict[str, str]:
        return {
            "apikey": api_key,
            "Content-Type": "application/json",
        }

    def _send_evolution_text(self, chat_id: str, message: str) -> None:
        base, api_key, instance = self._evolution_base()
        url = f"{base}/message/sendText/{instance}"
        payload = {
            "number": _evolution_number(chat_id),
            "text": message,
        }
        response = requests.post(
            url,
            json=payload,
            headers=self._evolution_headers(api_key),
            timeout=30,
        )
        if not response.ok:
            raise RuntimeError(
                f"Evolution API {response.status_code} — {response.text[:400]}"
            )
        log.info("Evolution API text sent to %s", chat_id)

    def _send_evolution_image(self, chat_id: str, image_path: Path, caption: str) -> None:
        base, api_key, instance = self._evolution_base()
        url = f"{base}/message/sendMedia/{instance}"
        media_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "number": _evolution_number(chat_id),
            "mediatype": "image",
            "mimetype": "image/png",
            "caption": caption[:1024],
            "media": media_b64,
            "fileName": image_path.name,
        }
        response = requests.post(
            url,
            json=payload,
            headers=self._evolution_headers(api_key),
            timeout=90,
        )
        if not response.ok:
            raise RuntimeError(
                f"Evolution API media {response.status_code} — {response.text[:400]}"
            )
        log.info("Evolution API image sent to %s (caption: %s)", chat_id, caption)

    # --- Custom webhook (your server / Zapier / internal bridge) ---
    def _send_webhook_text(self, chat_id: str, message: str) -> None:
        url = os.environ["WHATSAPP_WEBHOOK_URL"]
        response = requests.post(
            url,
            json={"chatId": chat_id, "message": message, "caption": message},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        log.info("Webhook text sent to %s", chat_id)

    def _send_webhook_file(self, chat_id: str, image_path: Path, caption: str) -> None:
        url = os.environ["WHATSAPP_WEBHOOK_URL"]
        with image_path.open("rb") as handle:
            response = requests.post(
                url,
                data={"chatId": chat_id, "caption": caption},
                files={"image": (image_path.name, handle, "image/png")},
                timeout=90,
            )
        response.raise_for_status()
        log.info("Webhook image sent to %s (caption: %s)", chat_id, caption)
