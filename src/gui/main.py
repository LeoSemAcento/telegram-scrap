import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import queue
import threading
import logging
import sys
from scraper.config_manager import ConfigManager
from scraper.worker import ScraperWorker

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            "gui.log", encoding="utf-8"
        ),  # Garante UTF-8 para o arquivo de log
        logging.StreamHandler(
            sys.stdout
        ),  # Usar sys.stdout para garantir que o encoding do terminal seja respeitado
    ],
)
# Configurar o encoding do console para UTF-8, se possível
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)


class TelegramScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Scraper")
        self.root.geometry("700x500")

        self.config_manager = ConfigManager()
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()

        self.worker = ScraperWorker(
            self.config_manager, self.request_queue, self.response_queue
        )
        self.worker_thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker_thread.start()

        self.controls = {}  # Dicionário para guardar os widgets
        self.setup_gui()
        self.process_responses()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # --- Coluna de Ações ---
        actions_frame = ttk.LabelFrame(main_frame, text="Ações", padding="10")
        actions_frame.grid(row=0, column=0, sticky=(tk.N, tk.S))

        self.controls["connect_button"] = ttk.Button(
            actions_frame, text="Conectar ao Telegram", command=self.connect_telegram
        )
        self.controls["connect_button"].pack(fill=tk.X, pady=5)

        self.controls["list_channels_button"] = ttk.Button(
            actions_frame,
            text="Listar Canais",
            command=lambda: self.send_command("list_channels"),
        )
        self.controls["list_channels_button"].pack(fill=tk.X, pady=5)

        self.controls["add_channel_button"] = ttk.Button(
            actions_frame, text="Adicionar Canal", command=self.add_channel
        )
        self.controls["add_channel_button"].pack(fill=tk.X, pady=5)

        self.controls["remove_channel_button"] = ttk.Button(
            actions_frame, text="Remover Canal", command=self.remove_channel
        )
        self.controls["remove_channel_button"].pack(fill=tk.X, pady=5)

        self.controls["scrape_channels_button"] = ttk.Button(
            actions_frame,
            text="Raspar Canais",
            command=lambda: self.send_command("scrape_channels"),
        )
        self.controls["scrape_channels_button"].pack(fill=tk.X, pady=5)

        self.controls["export_data_button"] = ttk.Button(
            actions_frame,
            text="Exportar Dados",
            command=lambda: self.send_command("export_data"),
        )
        self.controls["export_data_button"].pack(fill=tk.X, pady=5)

        self.controls["export_ids_button"] = ttk.Button(
            actions_frame,
            text="Exportar IDs",
            command=lambda: self.send_command("export_ids"),
        )
        self.controls["export_ids_button"].pack(fill=tk.X, pady=5)

        # --- Coluna de Configurações ---
        settings_frame = ttk.LabelFrame(main_frame, text="Configurações", padding="10")
        settings_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))

        self.continuous_scraping_var = tk.BooleanVar(
            value=self.config_manager.get("scraping.continuous_scraping", False)
        )
        self.controls["continuous_scraping_check"] = ttk.Checkbutton(
            settings_frame,
            text="Raspagem Contínua",
            variable=self.continuous_scraping_var,
            command=self.toggle_continuous_scraping,
        )
        self.controls["continuous_scraping_check"].pack(anchor=tk.W)

        self.download_media_var = tk.BooleanVar(
            value=self.config_manager.get("scraping.download_media", False)
        )
        self.controls["download_media_check"] = ttk.Checkbutton(
            settings_frame,
            text="Download de Mídia",
            variable=self.download_media_var,
            command=self.toggle_media_download,
        )
        self.controls["download_media_check"].pack(anchor=tk.W)

        self.toggle_controls(False)  # Desabilitar controles na inicialização

        # --- Área de Logs ---
        log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="10")
        log_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=20, width=60)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log("Bem-vindo ao Telegram Scraper!")

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        logging.info(message)

    def send_command(self, command, **kwargs):
        self.request_queue.put({"command": command, "args": kwargs})

    def process_responses(self):
        try:
            response = self.response_queue.get_nowait()
            status = response.get("status")
            message = response.get("message")
            data = response.get("data")

            if status == "log":
                self.log(message)
            elif status == "error":
                self.log(f"ERRO: {message}")
                messagebox.showerror("Erro", message)
            elif status == "success":
                self.log(f"SUCESSO: {message}")
                if message == "Conectado com sucesso!":
                    self.toggle_controls(True)
            elif status == "channels_list":
                self.log("Canais e Grupos disponíveis:")
                for item in data:
                    self.log(f"Canal/Grupo: {item['name']} (ID: {item['id']})")
                    if "topics" in item and item["topics"]:
                        for topic in item["topics"]:
                            self.log(f"  - Tópico: {topic['name']} (ID: {topic['id']})")
                self.log(
                    "Extração de canais e grupos concluída."
                )  # Adicionado mensagem de conclusão
            elif status == "request_2fa_code":
                self.prompt_for_2fa_code()
            elif status == "request_password":
                self.prompt_for_password()

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_responses)

    def prompt_for_password(self):
        """Pede a senha de 2FA ao usuário e a envia para o worker."""
        password = simpledialog.askstring(
            "Senha de Verificação",
            "Por favor, insira sua senha de autenticação de dois fatores:",
            parent=self.root,
            show="*",  # Esconde a senha
        )
        self.worker.password_queue.put(password)

    def toggle_controls(self, enabled):
        """Habilita ou desabilita os controles da GUI, exceto o de conexão."""
        state = tk.NORMAL if enabled else tk.DISABLED
        for name, widget in self.controls.items():
            if name != "connect_button":
                widget.config(state=state)

    def prompt_for_2fa_code(self):
        """Pede o código 2FA ao usuário e o envia para o worker."""
        code = simpledialog.askstring(
            "Código de Verificação",
            "Por favor, insira o código que você recebeu no Telegram:",
            parent=self.root,
        )
        # Envia o código (ou None se o usuário cancelar) para a fila do worker
        self.worker.code_queue.put(code)

    def connect_telegram(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Credenciais do Telegram")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Carregar credenciais existentes para preencher os campos
        api_id = self.config_manager.get("telegram.api_id", "")
        api_hash = self.config_manager.get("telegram.api_hash", "")
        phone = self.config_manager.get("telegram.phone_number", "")

        ttk.Label(dialog, text="API ID:").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W
        )
        api_id_entry = ttk.Entry(dialog)
        api_id_entry.grid(row=0, column=1, padx=5, pady=5)
        api_id_entry.insert(0, api_id)

        ttk.Label(dialog, text="API Hash:").grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W
        )
        api_hash_entry = ttk.Entry(dialog)
        api_hash_entry.grid(row=1, column=1, padx=5, pady=5)
        api_hash_entry.insert(0, api_hash)

        ttk.Label(dialog, text="Número de Telefone:").grid(
            row=2, column=0, padx=5, pady=5, sticky=tk.W
        )
        phone_entry = ttk.Entry(dialog)
        phone_entry.grid(row=2, column=1, padx=5, pady=5)
        phone_entry.insert(0, phone)

        def confirm():
            try:
                api_id_val = int(api_id_entry.get())
                api_hash_val = api_hash_entry.get()
                phone_val = phone_entry.get()

                if not all([api_id_val, api_hash_val, phone_val]):
                    messagebox.showerror("Erro", "Todos os campos são obrigatórios.")
                    return

                self.send_command(
                    "connect",
                    api_id=api_id_val,
                    api_hash=api_hash_val,
                    phone_number=phone_val,
                )
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Erro", "API ID deve ser um número inteiro.")
            except Exception as e:
                messagebox.showerror("Erro", f"Ocorreu um erro: {e}")

        ttk.Button(dialog, text="Confirmar", command=confirm).grid(
            row=3, column=0, columnspan=2, pady=10
        )

    def add_channel(self):
        channel_id = simpledialog.askstring(
            "Adicionar Canal", "Digite o ID ou nome do canal:"
        )
        if channel_id:
            self.send_command(
                "add_channel", channel_id=channel_id, channel_name=channel_id
            )

    def remove_channel(self):
        channel_id = simpledialog.askstring(
            "Remover Canal", "Digite o ID ou nome do canal:"
        )
        if channel_id:
            self.send_command("remove_channel", channel_id=channel_id)

    def toggle_continuous_scraping(self):
        is_enabled = self.continuous_scraping_var.get()
        self.send_command("toggle_continuous_scraping", enabled=is_enabled)

    def toggle_media_download(self):
        is_enabled = self.download_media_var.get()
        self.send_command("toggle_media_download", enabled=is_enabled)

    def on_closing(self):
        self.log("Encerrando a aplicação...")
        self.send_command("shutdown")
        # Aguardar um pouco para o worker processar o shutdown
        self.root.after(500, self.root.destroy)


if __name__ == "__main__":
    root = tk.Tk()
    app = TelegramScraperGUI(root)
    root.mainloop()
