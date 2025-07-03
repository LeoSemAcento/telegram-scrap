import asyncio
import queue
import logging
from scraper.client import TelegramScraper
from scraper.id_exporter import TelegramIDExporter
from scraper.config_manager import ConfigManager
from telethon.errors.rpcerrorlist import SessionPasswordNeededError


class ScraperWorker:
    def __init__(self, config_manager, request_queue, response_queue):
        self.config_manager = config_manager
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.code_queue = queue.Queue()  # Fila dedicada para o código 2FA
        self.password_queue = queue.Queue()  # Fila dedicada para a senha 2FA
        self.scraper = None
        self.id_exporter = None
        self.loop = None
        self.shutdown_event = asyncio.Event()

    def run(self):
        """Ponto de entrada principal para a thread do worker."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.main_loop())

    async def main_loop(self):
        """Loop principal que processa comandos e executa tarefas."""
        logging.info("Worker thread started.")
        while not self.shutdown_event.is_set():
            try:
                request = self.request_queue.get_nowait()
                command = request.get("command")
                args = request.get("args", {})

                if command == "shutdown":
                    await self.shutdown()
                    break

                await self.handle_command(command, args)

            except queue.Empty:
                await asyncio.sleep(0.1)
            except Exception as e:
                self.post_error(f"Erro inesperado no worker: {e}")
        logging.info("Worker thread finished.")

    async def handle_command(self, command, args):
        """Direciona o comando para o método apropriado."""
        handler = getattr(self, f"handle_{command}", None)
        if handler:
            try:
                await handler(**args)
            except Exception as e:
                self.post_error(f"Erro ao executar '{command}': {e}")
        else:
            self.post_error(f"Comando desconhecido: {command}")

    def post_response(self, status, message=None, data=None):
        """Envia uma resposta de volta para a GUI."""
        self.response_queue.put({"status": status, "message": message, "data": data})

    def post_log(self, message):
        self.post_response("log", message)

    def post_error(self, message):
        logging.error(message)
        self.post_response("error", message)

    def post_success(self, message):
        self.post_response("success", message)

    # --- Handlers de Comando ---

    async def handle_connect(self, api_id, api_hash, phone_number):
        """Lida com a tentativa de conexão."""
        self.post_log("Configurando credenciais...")
        self.config_manager.set("telegram.api_id", api_id)
        self.config_manager.set("telegram.api_hash", api_hash)
        self.config_manager.set("telegram.phone_number", phone_number)

        self.scraper = TelegramScraper(self.config_manager)

        def get_code_callback():
            """Função de callback que interage com a GUI para obter o código."""
            self.post_response("request_2fa_code")
            # Bloqueia a thread do worker até que o código seja recebido da GUI
            return self.code_queue.get()

        try:
            self.post_log("Conectando ao Telegram...")
            await self.scraper.start(code_callback=get_code_callback)
            self.id_exporter = TelegramIDExporter(self.scraper.client)
            self.post_success("Conectado com sucesso!")
        except SessionPasswordNeededError:
            self.post_response("request_password")
            password = self.password_queue.get()  # Espera a senha da GUI
            if password:
                try:
                    await self.scraper.start(
                        password=password
                    )  # Não passa phone novamente
                    self.id_exporter = TelegramIDExporter(self.scraper.client)
                    self.post_success("Conectado com sucesso!")
                except Exception as e:
                    self.scraper = None
                    self.post_error(f"Falha na conexão (senha): {e}")
            else:
                self.scraper = None
                self.post_error("Conexão cancelada: senha de 2FA não fornecida.")
        except Exception as e:
            self.scraper = None
            self.post_error(f"Falha na conexão: {e}")

    async def handle_list_channels(self):
        if not self.scraper:
            return self.post_error("Não conectado. Por favor, conecte-se primeiro.")
        self.post_log("Buscando lista de canais e grupos...")
        try:
            channels_and_groups = await self.scraper.get_channels_and_groups()
            if channels_and_groups:
                self.response_queue.put(
                    {"status": "channels_list", "data": channels_and_groups}
                )
            else:
                self.post_log("Nenhum canal ou grupo encontrado.")
        except Exception as e:
            self.post_error(f"Erro ao listar canais e grupos: {e}")

    async def handle_scrape_channels(self):
        if not self.scraper:
            return self.post_error("Não conectado. Por favor, conecte-se primeiro.")
        self.post_log("Iniciando raspagem de canais e grupos...")
        try:
            # Obter a lista completa de canais e grupos, incluindo tópicos
            channels_and_groups = await self.scraper.get_channels_and_groups()

            if not channels_and_groups:
                self.post_log("Nenhum canal ou grupo para raspar.")
                return

            for item in channels_and_groups:
                # O usuário não quer raspar tópicos, apenas listar grupos/canais principais.
                # A lógica de scraping será aplicada apenas aos itens de nível superior.
                self.post_log(
                    f"Raspando canal/grupo: {item['name']} (ID: {item['id']})"
                )
                await self.scraper.scrape_channel(
                    channel_id=item["id"], channel_name=item["name"]
                )
            self.post_success("Raspagem de canais e grupos concluída.")
        except Exception as e:
            self.post_error(f"Erro durante a raspagem: {e}")

    async def handle_add_channel(self, channel_id, channel_name):
        self.config_manager.add_channel(channel_id, channel_name)
        self.post_success(f"Canal '{channel_name}' adicionado à configuração.")

    async def handle_remove_channel(self, channel_id):
        self.config_manager.remove_channel(channel_id)
        self.post_success(f"Canal com ID '{channel_id}' removido da configuração.")

    async def handle_toggle_continuous_scraping(self, enabled):
        self.config_manager.set("scraping.continuous_scraping", enabled)
        status = "ativada" if enabled else "desativada"
        self.post_success(f"Raspagem contínua {status}.")
        if enabled:
            # Inicia a tarefa em background
            self.loop.create_task(self.scraper.continuous_scraping())

    async def handle_toggle_media_download(self, enabled):
        self.config_manager.set("scraping.download_media", enabled)
        status = "ativado" if enabled else "desativado"
        self.post_success(f"Download de mídia {status}.")

    async def shutdown(self):
        """Encerra o worker e os recursos de forma limpa."""
        self.post_log("Desligando o worker...")
        self.shutdown_event.set()
        if self.scraper and self.scraper.client.is_connected():
            await self.scraper.client.disconnect()
            self.post_log("Cliente do Telegram desconectado.")
