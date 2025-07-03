import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, types
from telethon.tl.functions.channels import GetForumTopicsRequest
import os


class TelegramIDExporter:
    def __init__(self, client):
        self.client = client
        self.setup_logging()

    def setup_logging(self):
        # Log do sistema para registrar eventos gerais e erros
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="system.log",
            filemode="w",
            encoding="utf-8",
        )

        # Log de download para registrar os grupos e tópicos extraídos
        self.download_logger = logging.getLogger("download")
        download_handler = logging.FileHandler(
            "download.log", mode="w", encoding="utf-8"
        )
        download_formatter = logging.Formatter("%(asctime)s - %(message)s")
        download_handler.setFormatter(download_formatter)
        self.download_logger.addHandler(download_handler)
        self.download_logger.setLevel(logging.INFO)

    async def export_groups_and_topics(self, output_file="grupos_ids.txt"):
        logging.info("Iniciando a extração de grupos, canais e tópicos.")
        print("Obtendo lista de grupos, canais e tópicos...")

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                async for dialog in self.client.iter_dialogs():
                    if not (dialog.is_group or dialog.is_channel):
                        continue

                    try:
                        entity = await self.client.get_entity(dialog.id)

                        # Escreve no arquivo e registra no log de download
                        f.write(f"{entity.title}\n")
                        f.write(f"{entity.id}\n")
                        self.download_logger.info(
                            f"Grupo/Canal: {entity.title} | ID: {entity.id}"
                        )

                        # Verifica se é um fórum e extrai os tópicos
                        if getattr(entity, "forum", False):
                            topics_result = await self.client(
                                GetForumTopicsRequest(
                                    channel=entity,
                                    offset_date=datetime.now(),
                                    offset_id=0,
                                    offset_topic=0,
                                    limit=100,
                                )
                            )
                            for topic in topics_result.topics:
                                if isinstance(topic, types.ForumTopic):
                                    f.write(f"\t{topic.title}\n")
                                    f.write(f"\t{topic.id}\n")
                                    self.download_logger.info(
                                        f"  Tópico: {topic.title} | ID: {topic.id} (Grupo: {entity.title})"
                                    )

                    except Exception as e:
                        logging.error(
                            f"Falha ao processar o diálogo '{dialog.name}' (ID: {dialog.id}): {e}"
                        )
                        print(f"Erro ao processar '{dialog.name}': {e}")

            print(f"Exportação concluída. Arquivo '{output_file}' criado.")
            logging.info("Exportação concluída com sucesso.")
            return True

        except Exception as e:
            logging.critical(f"Ocorreu um erro fatal no script: {e}")
            print(f"Ocorreu um erro crítico: {e}")
            return False
