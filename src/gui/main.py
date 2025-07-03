import tkinter as tk
from tkinter import ttk, messagebox
import os
import asyncio
import threading
from src.scraper.client import TelegramScraper
from src.scraper.id_exporter import TelegramIDExporter


class TelegramScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Scraper")
        self.root.geometry("600x400")
        self.scraper = None
        self.id_exporter = None
        self.config_path = "config/config.yaml"
        self.setup_gui()
        self.loop = asyncio.get_event_loop()

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
        def run():
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future.result()

        thread = threading.Thread(target=run)
        thread.start()
        return thread

    def connect_telegram(self):
        if not self.scraper:
            self.scraper = TelegramScraper(self.config_path)
            self.id_exporter = TelegramIDExporter(self.scraper.client)
            self.run_async(self.scraper.start())
            self.log("Conectando ao Telegram... Aguarde.")
        else:
            self.log("Já conectado ao Telegram.")

    def list_channels(self):
        if not self.scraper:
            self.log("Conecte-se ao Telegram primeiro.")
            return
        channels = self.run_async(self.scraper.get_channels())
        self.log("Canais disponíveis:")
        for ch in channels:
            self.log(f"- {ch.name} (ID: {ch.id})")

    def add_channel(self):
        if not self.scraper:
            self.log("Conecte-se ao Telegram primeiro.")
            return
        channel_id = tk.simpledialog.askstring(
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
        channel_id = tk.simpledialog.askstring(
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
            self.run_async(self.scraper.scrape_channel(ch_id))
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
            self.run_async(self.scraper.continuous_scraping())
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
        self.run_async(self.id_exporter.export_groups_and_topics())
        self.log("Iniciando exportação de IDs de grupos e tópicos...")


if __name__ == "__main__":
    root = tk.Tk()
    app = TelegramScraperGUI(root)
    root.mainloop()
