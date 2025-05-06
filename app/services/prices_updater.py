from typing import Optional
from datetime import datetime
from aiogram import Bot


class PriceUpdater:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.active_updates = {}
            cls._instance.bot = None
        return cls._instance

    def set_bot(self, bot: Bot):
        self.bot = bot

    def add_update_task(self, chat_id: int, message_id: int, pairs: list):
        self.active_updates[(chat_id, message_id)] = {
            'pairs': pairs,
            'last_prices': {pair: None for pair in pairs},
            'running': True,
            'last_update': datetime.utcnow()
        }

    def stop_update_task(self, chat_id: int, message_id: int):
        key = (chat_id, message_id)
        if key in self.active_updates:
            self.active_updates[key]['running'] = False
            return True
        return False

    def is_running(self, chat_id: int, message_id: int) -> bool:
        key = (chat_id, message_id)
        if key in self.active_updates:
            return self.active_updates[key]['running']
        return False

    def update_last_prices(self, chat_id: int, message_id: int, prices: dict):
        key = (chat_id, message_id)
        if key in self.active_updates:
            self.active_updates[key]['last_prices'] = prices
            self.active_updates[key]['last_update'] = datetime.utcnow()

    def get_last_prices(self, chat_id: int, message_id: int) -> Optional[dict]:
        key = (chat_id, message_id)
        if key in self.active_updates:
            return self.active_updates[key]['last_prices']
        return None

    def remove_task(self, chat_id: int, message_id: int):
        key = (chat_id, message_id)
        if key in self.active_updates:
            del self.active_updates[key]