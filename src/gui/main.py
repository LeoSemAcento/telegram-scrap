import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import asyncio
import threading
import sys
import yaml
import queue

# Adiciona o diretório raiz do projeto ao caminho de busca do Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(project_root)

# Adiciona o diretório 'src' ao caminho de busca
src_dir = os.path.join(project_root, "src")
sys.path.append(src_dir)

# Importa os módulos necessários
try:
    from scraper.client import TelegramScraper
    from scraper.id_exporter import TelegramIDExporter
except ImportError:
    print("Erro ao importar módulos. Caminho de busca do Python:")
    for path in sys.path:
        print(path)
    raise


class TelegramScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Scraper")
        self.root.geometry("600x400")
        self.scraper = None
        self.id_exporter = None
        self.config_path = os.path.join(project_root, "config", "config.yaml")
        self.setup_gui()
        self.loop = (
            asyncio.new_event_loop()
        )  # Cria um novo loop de eventos para evitar conflitos com o loop principal do Tkinter
        threading.Thread(
            target=self.start_loop, daemon=True
        ).start()  # Inicia o loop em uma thread separada

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def setup_gui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Botões para ações
        ttk.Button(
            main_frame, text="Conectar ao Telegram", command=self.connect_telegram
        ).grid(row=0, column=0, pady=5, padx=5, sticky=tk.W)
        ttk.Button(main_frame, text="Listar Canais", command=self.list_channels).grid(
            row=1, column=0, pady=5, padx=5, sticky=tk.W
        )
        ttk.Button(main_frame, text="Adicionar Canal", command=self.add_channel).grid(
            row=2, column=0, pady=5, padx=5, sticky=tk.W
        )
        ttk.Button(main_frame, text="Remover Canal", command=self.remove_channel).grid(
            row=3, column=0, pady=5, padx=5, sticky=tk.W
        )
        ttk.Button(main_frame, text="Raspar Canais", command=self.scrape_channels).grid(
            row=4, column=0, pady=5, padx=5, sticky=tk.W
        )
        ttk.Button(main_frame, text="Exportar Dados", command=self.export_data).grid(
            row=5, column=0, pady=5, padx=5, sticky=tk.W
        )
        ttk.Button(
            main_frame,
            text="Ativar Raspagem Contínua",
            command=self.toggle_continuous_scraping,
        ).grid(row=6, column=0, pady=5, padx=5, sticky=tk.W)
        ttk.Button(
            main_frame,
            text="Ativar/Desativar Download de Mídia",
            command=self.toggle_media_download,
        ).grid(row=7, column=0, pady=5, padx=5, sticky=tk.W)
        ttk.Button(
            main_frame,
            text="Exportar IDs de Grupos e Tópicos",
            command=self.export_groups_and_topics,
        ).grid(row=8, column=0, pady=5, padx=5, sticky=tk.W)

        # Área de texto para logs
        self.log_text = tk.Text(main_frame, height=10, width=50)
        self.log_text.grid(row=0, column=1, rowspan=9, pady=5, padx=5)
        self.log_text.insert(tk.END, "Bem-vindo ao Telegram Scraper!\n")

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def run_async(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    def connect_telegram(self):
        # Sempre abre o diálogo para permitir novas tentativas de conexão.
        self.show_credentials_dialog()

    def show_credentials_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Credenciais do Telegram")

        # Centralizar a janela de pop-up
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        dialog.geometry(f"300x200+{x + w // 2 - 150}+{y + h // 2 - 100}")

        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="API ID:").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W
        )
        api_id_entry = ttk.Entry(dialog)
        api_id_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="API Hash:").grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W
        )
        api_hash_entry = ttk.Entry(dialog)
        api_hash_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Número de Telefone:").grid(
            row=2, column=0, padx=5, pady=5, sticky=tk.W
        )
        phone_entry = ttk.Entry(dialog)
        phone_entry.grid(row=2, column=1, padx=5, pady=5)

        def confirm():
            try:
                api_id = int(api_id_entry.get())
                api_hash = api_hash_entry.get()
                phone_number = phone_entry.get()

                # Atualizar configuração
                config = {
                    "telegram": {
                        "api_id": api_id,
                        "api_hash": api_hash,
                        "phone_number": phone_number,
                        "session_file": "session.session",
                    },
                    "scraping": {
                        "channels": [],
                        "message_limit": 100,
                        "continuous_scraping": False,
                        "interval_seconds": 300,
                        "download_media": False,
                    },
                }
                with open(self.config_path, "w") as f:
                    yaml.safe_dump(config, f, default_flow_style=False)

                # Conectar de forma assíncrona e tratar o resultado
                def connect_async():
                    # Define o event loop para esta thread específica.
                    asyncio.set_event_loop(asyncio.new_event_loop())
                    try:
                        # Cria uma nova instância do scraper para cada tentativa.
                        scraper_instance = TelegramScraper(self.config_path)

                        # Esta função será chamada pelo Telethon quando precisar do código.
                        def get_code_from_dialog():
                            self.log(
                                "Um código de verificação é necessário. Abrindo pop-up..."
                            )
                            q = queue.Queue()

                            def ask_on_main_thread():
                                code = simpledialog.askstring(
                                    "Código de Verificação",
                                    "Por favor, insira o código que você recebeu no Telegram:",
                                    parent=dialog,
                                )
                                q.put(code)

                            self.root.after(0, ask_on_main_thread)
                            return q.get()

                        # O método start agora é chamado diretamente, pois já estamos em uma thread.
                        # Usamos o loop da thread atual.
                        loop = asyncio.get_event_loop()
                        result = loop.run_until_complete(
                            scraper_instance.start(code_callback=get_code_from_dialog)
                        )

                        if result:
                            # Apenas atribui à instância principal em caso de sucesso.
                            self.scraper = scraper_instance
                            self.id_exporter = TelegramIDExporter(self.scraper.client)
                            self.root.after(
                                0, lambda: self.log("Conectado com sucesso!")
                            )
                            self.root.after(0, dialog.destroy)
                    except Exception as e:
                        self.root.after(
                            0,
                            lambda e=e: self.log(f"Erro na conexão: {str(e)}"),
                        )
                        self.root.after(
                            0,
                            lambda e=e: messagebox.showerror(
                                "Erro", f"Falha ao conectar: {str(e)}"
                            ),
                        )

                threading.Thread(target=connect_async, daemon=True).start()
                self.log("Conectando ao Telegram... Aguarde.")
            except ValueError:
                messagebox.showerror("Erro", "API ID deve ser um número inteiro.")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao conectar: {str(e)}")

        ttk.Button(dialog, text="Confirmar", command=confirm).grid(
            row=3, column=0, columnspan=2, pady=10
        )

    def list_channels(self):
        if not self.scraper:
            self.log("Conecte-se ao Telegram primeiro.")
            return

        def list_channels_async():
            try:
                channels = self.run_async(self.scraper.get_channels())
                self.root.after(0, lambda: self.log("Canais disponíveis:"))
                for ch in channels:
                    self.root.after(
                        0, lambda ch=ch: self.log(f"- {ch.name} (ID: {ch.id})")
                    )
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Erro ao listar canais: {str(e)}"))

        threading.Thread(target=list_channels_async, daemon=True).start()

    def add_channel(self):
        if not self.scraper:
            self.log("Conecte-se ao Telegram primeiro.")
            return
        channel_id = simpledialog.askstring(
            "Adicionar Canal", "Digite o ID ou nome do canal:"
        )
        if channel_id:
            self.scraper.config["scraping"]["channels"].append(
                {"id": channel_id, "name": channel_id}
            )
            self.log(f"Canal {channel_id} adicionado.")
            # Salvar configuração
            with open(self.config_path, "w") as f:
                yaml.safe_dump(self.scraper.config, f, default_flow_style=False)

    def remove_channel(self):
        if not self.scraper:
            self.log("Conecte-se ao Telegram primeiro.")
            return
        channel_id = simpledialog.askstring(
            "Remover Canal", "Digite o ID ou nome do canal:"
        )
        if channel_id:
            self.scraper.config["scraping"]["channels"] = [
                ch
                for ch in self.scraper.config["scraping"]["channels"]
                if ch["id"] != channel_id
            ]
            self.log(f"Canal {channel_id} removido.")
            # Salvar configuração
            with open(self.config_path, "w") as f:
                yaml.safe_dump(self.scraper.config, f, default_flow_style=False)

    def scrape_channels(self):
        if not self.scraper:
            self.log("Conecte-se ao Telegram primeiro.")
            return
        channels = [ch["id"] for ch in self.scraper.config["scraping"]["channels"]]
        if not channels:
            self.log("Nenhum canal configurado para raspagem.")
            return
        for ch_id in channels:
            threading.Thread(
                target=lambda: self.run_async(self.scraper.scrape_channel(ch_id)),
                daemon=True,
            ).start()
            self.log(f"Iniciando raspagem do canal {ch_id}...")

    def export_data(self):
        if not self.scraper:
            self.log("Conecte-se ao Telegram primeiro.")
            return
        channels = [ch["id"] for ch in self.scraper.config["scraping"]["channels"]]
        if not channels:
            self.log("Nenhum canal configurado para exportação.")
            return
        for ch_id in channels:
            self.scraper.export_data(ch_id)
            self.log(f"Dados exportados para o canal {ch_id}.")

    def toggle_continuous_scraping(self):
        if not self.scraper:
            self.log("Conecte-se ao Telegram primeiro.")
            return
        self.scraper.config["scraping"]["continuous_scraping"] = (
            not self.scraper.config["scraping"]["continuous_scraping"]
        )
        status = (
            "ativada"
            if self.scraper.config["scraping"]["continuous_scraping"]
            else "desativada"
        )
        self.log(f"Raspagem contínua {status}.")
        if self.scraper.config["scraping"]["continuous_scraping"]:
            threading.Thread(
                target=lambda: self.run_async(self.scraper.continuous_scraping()),
                daemon=True,
            ).start()
        # Salvar configuração
        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.scraper.config, f, default_flow_style=False)

    def toggle_media_download(self):
        if not self.scraper:
            self.log("Conecte-se ao Telegram primeiro.")
            return
        self.scraper.config["scraping"]["download_media"] = not self.scraper.config[
            "scraping"
        ]["download_media"]
        status = (
            "ativado"
            if self.scraper.config["scraping"]["download_media"]
            else "desativado"
        )
        self.log(f"Download de mídia {status}.")
        # Salvar configuração
        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.scraper.config, f, default_flow_style=False)

    def export_groups_and_topics(self):
        if not self.id_exporter:
            self.log("Conecte-se ao Telegram primeiro.")
            return
        threading.Thread(
            target=lambda: self.run_async(self.id_exporter.export_groups_and_topics()),
            daemon=True,
        ).start()
        self.log("Iniciando exportação de IDs de grupos e tópicos...")


if __name__ == "__main__":
    root = tk.Tk()
    app = TelegramScraperGUI(root)
    root.mainloop()
