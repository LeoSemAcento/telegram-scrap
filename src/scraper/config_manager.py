import yaml
import os
import threading


class ConfigManager:
    def __init__(self, config_path="config/config.yaml"):
        self.config_path = config_path
        self.config = {}
        self._lock = threading.Lock()
        self.load_config()

    def load_config(self):
        """Carrega a configuração do arquivo YAML. Se o arquivo não existir, cria um com valores padrão."""
        with self._lock:
            try:
                with open(self.config_path, "r") as f:
                    self.config = yaml.safe_load(f) or {}
            except FileNotFoundError:
                self.config = self.get_default_config()
                self.save_config()

    def get_default_config(self):
        """Retorna a estrutura de configuração padrão."""
        return {
            "telegram": {
                "api_id": "",
                "api_hash": "",
                "phone_number": "",
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

    def get(self, key, default=None):
        """Obtém um valor de configuração usando uma chave aninhada (ex: 'telegram.api_id')."""
        with self._lock:
            keys = key.split(".")
            value = self.config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

    def set(self, key, value):
        """Define um valor de configuração usando uma chave aninhada."""
        with self._lock:
            keys = key.split(".")
            d = self.config
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value
        self.save_config()

    def save_config(self):
        """Salva a configuração atual no arquivo YAML."""
        with self._lock:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w") as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)

    def add_channel(self, channel_id, channel_name):
        """Adiciona um novo canal à lista de scraping."""
        with self._lock:
            channels = self.get("scraping.channels", [])
            # Evitar duplicatas
            if not any(c["id"] == channel_id for c in channels):
                channels.append({"id": channel_id, "name": channel_name})
                self.set("scraping.channels", channels)

    def remove_channel(self, channel_id):
        """Remove um canal da lista de scraping."""
        with self._lock:
            channels = self.get("scraping.channels", [])
            updated_channels = [c for c in channels if c["id"] != channel_id]
            self.set("scraping.channels", updated_channels)
