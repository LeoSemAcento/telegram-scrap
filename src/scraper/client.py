import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import (
    PeerChannel,
    Channel,
    ChannelForbidden,
    User,
    Chat,
    Message,
)
from telethon.errors import FloodWaitError, RPCError
import logging
import os  # Adicionado para operações de arquivo
import re  # Adicionado para sanitização
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


def sanitize_name(name: str) -> str:
    """Sanitiza um nome para uso em nomes de arquivos/pastas, substituindo caracteres especiais por underscores."""
    # Substitui caracteres não alfanuméricos (exceto espaços) por '_'
    s = re.sub(r"[^\w\s-]", "", name)
    # Substitui espaços e hífens por '_'
    s = re.sub(r"[\s-]+", "_", s).strip("_")
    return s


class TelegramScraper:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.client = TelegramClient(
            self.config_manager.get("telegram.session_file"),
            self.config_manager.get("telegram.api_id"),
            self.config_manager.get("telegram.api_hash"),
        )
        self.register_event_handlers()

    def register_event_handlers(self):
        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            if self.config_manager.get("scraping.continuous_scraping"):
                channel_id = event.chat_id
                channels = self.config_manager.get("scraping.channels", [])
                if any(ch["id"] == channel_id for ch in channels):
                    await self.process_message(event.message, channel_id)

    async def start(self, code_callback=None, password=None):
        """Inicia o cliente Telegram, com callbacks para código e senha 2FA."""
        phone_number = self.config_manager.get("telegram.phone_number")
        await self.client.start(
            phone=phone_number, code_callback=code_callback, password=password
        )
        return True

    async def run_until_disconnected(self):
        await self.client.run_until_disconnected()

    async def get_channels(self):
        # Este método não será mais usado diretamente, mas mantido por compatibilidade
        dialogs = await self.client.get_dialogs()
        return [d for d in dialogs if isinstance(d.entity, PeerChannel)]

    async def get_channels_and_groups(self):
        """Obtém uma lista formatada de canais, grupos e seus tópicos."""
        result = []
        try:
            async for (
                d
            ) in self.client.iter_dialogs():  # Corrigido o erro de sintaxe aqui
                entity = d.entity
                item_data = None

                if isinstance(entity, Channel):
                    # Canais e Supergrupos (que podem ter tópicos)
                    if entity.megagroup and entity.forum:  # É um supergrupo com tópicos
                        topics = []
                        try:
                            # Para obter tópicos, iteramos sobre as mensagens do canal
                            # e consideramos mensagens que não são respostas como potenciais tópicos.
                            # Isso pode não ser 100% preciso para todos os casos de fóruns do Telegram,
                            # mas é uma abordagem genérica.
                            async for msg in self.client.iter_messages(
                                entity, limit=50
                            ):  # Limite para evitar sobrecarga
                                if (
                                    msg.reply_to is None
                                ):  # Mensagem que inicia uma nova thread/tópico
                                    topics.append(
                                        {
                                            "id": msg.id,
                                            "name": sanitize_name(
                                                msg.message or f"Tópico {msg.id}"
                                            ),  # Sanitizar nome do tópico
                                        }
                                    )
                                if (
                                    len(topics) >= 20
                                ):  # Limite de tópicos para evitar flood wait excessivo
                                    break

                            item_data = {
                                "id": entity.id,
                                "name": sanitize_name(
                                    entity.title
                                ),  # Sanitizar nome do grupo/canal
                                "type": "Supergrupo com Tópicos",
                                "topics": topics,
                            }
                        except Exception as e:
                            logger.warning(
                                f"Não foi possível obter tópicos para {sanitize_name(entity.title)}: {e}"
                            )

                    else:  # Canal ou Supergrupo sem tópicos
                        item_data = {
                            "id": entity.id,
                            "name": sanitize_name(
                                entity.title
                            ),  # Sanitizar nome do grupo/canal
                            "type": "Canal/Grupo",
                        }
                elif isinstance(entity, Chat):  # Grupos antigos
                    item_data = {
                        "id": entity.id,
                        "name": sanitize_name(
                            entity.title
                        ),  # Sanitizar nome do grupo/canal
                        "type": "Grupo Antigo",
                    }
                elif isinstance(entity, User):  # Usuários (ignorar para esta lista)
                    continue
                elif isinstance(entity, ChannelForbidden):  # Canais/Grupos proibidos
                    item_data = {
                        "id": entity.id,
                        "name": sanitize_name(
                            entity.title + " (Proibido)"
                        ),  # Sanitizar nome do grupo/canal
                        "type": "Proibido",
                    }

                if item_data:
                    result.append(item_data)

        except FloodWaitError as e:
            logger.warning(
                f"Flood wait por {e.seconds} segundos ao listar canais. Tentando novamente..."
            )
            await asyncio.sleep(e.seconds + 5)  # Espera um pouco mais
            return await self.get_channels_and_groups()  # Tenta novamente
        except RPCError as e:
            logger.error(f"Erro RPC ao listar canais: {e}")
            # Não post_error aqui, o worker fará isso
        except Exception as e:
            logger.error(f"Erro inesperado ao listar canais: {e}")
            # Não post_error aqui, o worker fará isso

        return result

    async def scrape_channel(self, channel_id, channel_name):
        channel = await self.client.get_entity(channel_id)
        limit = self.config_manager.get("scraping.message_limit")
        messages = await self.client.get_messages(channel, limit=limit)
        for msg in messages:
            await self.process_message(msg, channel_id, channel_name=channel_name)

    async def scrape_topic(self, channel_id, topic_id, channel_name, topic_name):
        channel = await self.client.get_entity(channel_id)
        limit = self.config_manager.get("scraping.message_limit")
        # Para tópicos, o Telethon usa reply_to para filtrar mensagens
        messages = await self.client.get_messages(
            channel, limit=limit, reply_to=topic_id
        )
        for msg in messages:
            await self.process_message(
                msg, channel_id, channel_name, topic_id, topic_name
            )

    async def process_message(
        self, message, channel_id, channel_name, topic_id=None, topic_name=None
    ):
        # Sanitizar nomes antes de usar em caminhos de arquivo
        sanitized_channel_name = sanitize_name(channel_name)
        sanitized_topic_name = sanitize_name(topic_name) if topic_name else None

        path_parts = ["scraped_data", sanitized_channel_name]
        if sanitized_topic_name:
            path_parts.append(sanitized_topic_name)

        save_dir = os.path.join(*path_parts)
        os.makedirs(save_dir, exist_ok=True)

        # Salvar texto da mensagem
        file_name = f"message_{message.id}.txt"
        file_path = os.path.join(save_dir, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"ID da Mensagem: {message.id}\n")
            f.write(f"Data: {message.date}\n")
            f.write(f"Remetente ID: {message.sender_id}\n")
            f.write(f"Texto: {message.text}\n")
            # Adicionar mais campos conforme necessário

        print(f"Mensagem {message.id} salva em {file_path}")
        logger.info(f"Mensagem {message.id} salva em {file_path}")

        # --- NOVO: Download de arquivos/documentos anexados ---
        if self.config_manager.get("scraping.download_media", False):
            # Verifica se a mensagem tem mídia/documento
            if hasattr(message, "document") and message.document:
                # Obtém o nome do arquivo
                file_name = None
                for attr in getattr(message.document, "attributes", []):
                    if hasattr(attr, "file_name"):
                        file_name = attr.file_name
                        break
                if not file_name:
                    # Nome genérico se não encontrar
                    file_name = f"document_{message.id}"
                # Caminho completo para salvar
                file_path = os.path.join(save_dir, file_name)
                # Baixa o arquivo
                try:
                    await message.download_media(file_path)
                    print(f"Arquivo {file_name} baixado em {file_path}")
                    logger.info(f"Arquivo {file_name} baixado em {file_path}")
                except Exception as e:
                    print(f"Erro ao baixar arquivo {file_name}: {e}")
                    logger.error(f"Erro ao baixar arquivo {file_name}: {e}")

    def export_data(self, channel_id):
        print(f"Exportando dados do canal {channel_id}")

    async def continuous_scraping(self):
        while self.config_manager.get("scraping.continuous_scraping"):
            channels = self.config_manager.get("scraping.channels", [])
            for channel in channels:
                await self.scrape_channel(channel["id"])
            interval = self.config_manager.get("scraping.interval_seconds")
            await asyncio.sleep(interval)
