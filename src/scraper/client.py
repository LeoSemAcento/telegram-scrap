import os
import yaml
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel


class TelegramScraper:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config()
        self.client = TelegramClient(
            self.config["telegram"]["session_file"],
            self.config["telegram"]["api_id"],
            self.config["telegram"]["api_hash"],
        )
        self.register_event_handlers()

    def load_config(self):
        with open(self.config_path, "r") as file:
            return yaml.safe_load(file)

    def register_event_handlers(self):
        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            if self.config["scraping"]["continuous_scraping"]:
                channel_id = event.chat_id
                if any(
                    ch["id"] == channel_id for ch in self.config["scraping"]["channels"]
                ):
                    await self.process_message(event.message, channel_id)

    async def start(self, code_callback):
        # A função de início agora recebe um 'code_callback' diretamente da GUI.
        # O Telethon chamará essa função quando precisar do código.
        await self.client.start(
            phone=self.config["telegram"]["phone_number"],
            code_callback=code_callback,
        )
        return True  # Retorna True quando conectado com sucesso

    async def run_until_disconnected(self):
        await self.client.run_until_disconnected()

    async def get_channels(self):
        dialogs = await self.client.get_dialogs()
        return [d for d in dialogs if isinstance(d.entity, PeerChannel)]

    async def scrape_channel(self, channel_id):
        channel = await self.client.get_entity(channel_id)
        messages = await self.client.get_messages(
            channel, limit=self.config["scraping"]["message_limit"]
        )
        for msg in messages:
            await self.process_message(msg, channel_id)

    async def process_message(self, message, channel_id):
        # Aqui você implementaria a lógica para processar e salvar as mensagens
        print(f"Mensagem recebida no canal {channel_id}: {message.text}")

    def export_data(self, channel_id):
        # Implementação para exportar dados
        print(f"Exportando dados do canal {channel_id}")

    async def continuous_scraping(self):
        while self.config["scraping"]["continuous_scraping"]:
            for channel in self.config["scraping"]["channels"]:
                await self.scrape_channel(channel["id"])
            await asyncio.sleep(self.config["scraping"]["interval_seconds"])
