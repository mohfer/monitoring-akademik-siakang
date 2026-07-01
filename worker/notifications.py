"""Outbound notification channels: Telegram Bot API and WAHA (WhatsApp)."""

import re
import time

import requests

from .logging_setup import log


class Notifier:
    """Sends notifications to all configured channels."""

    def __init__(self, config):
        self.config = config

    def telegram(self, message):
        """Send a Markdown message via the Telegram Bot API."""
        c = self.config
        if not c.telegram_token or not c.chat_id:
            return

        url = f"https://api.telegram.org/bot{c.telegram_token}/sendMessage"
        payload = {"chat_id": c.chat_id, "text": message, "parse_mode": "Markdown"}

        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    return
                if 400 <= response.status_code < 500:
                    log(f"[WARNING] Telegram API Error: {response.text}")
                    return
            except Exception as e:
                log(f"[WARNING] Failed to send Telegram (Attempt {attempt + 1}/3): {e}")

            if attempt < 2:
                time.sleep(5)

    def waha(self, message):
        """Send a plain-text message via WAHA (WhatsApp HTTP API)."""
        c = self.config
        if not c.waha_base_url:
            return

        target_number = c.whatsapp_number
        if not target_number and c.chat_id and c.chat_id.isdigit():
            target_number = c.chat_id

        if not target_number:
            return

        wa_message = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1 (\2)', message)

        target_number = str(target_number).strip()

        if '@' not in target_number:
            sanitized = re.sub(r'[^0-9]', '', target_number)
            if sanitized:
                target_number = f"{sanitized}@c.us"

        url = f"{c.waha_base_url}/api/sendText"
        payload = {
            "chatId": target_number,
            "text": wa_message,
            "session": c.waha_session,
        }

        headers = {}
        if c.waha_api_key:
            headers["X-Api-Key"] = c.waha_api_key

        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                if response.status_code in (200, 201):
                    return
                log(f"[WARNING] WAHA API Error: {response.text}")
            except Exception as e:
                log(f"[WARNING] Failed to send WAHA (Attempt {attempt + 1}/3): {e}")

            if attempt < 2:
                time.sleep(2)

    def send_per_channel(self, telegram_msg=None, whatsapp_msg=None):
        """Send different messages to each channel."""
        c = self.config
        if telegram_msg and c.telegram_token and c.chat_id:
            self.telegram(telegram_msg)
        if whatsapp_msg and c.waha_base_url and c.whatsapp_number:
            self.waha(whatsapp_msg)

    def send(self, message):
        """Dispatch a message to every configured channel."""
        c = self.config
        if c.telegram_token and c.chat_id:
            self.telegram(message)

        if c.waha_base_url and c.whatsapp_number:
            self.waha(message)
