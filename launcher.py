import sys
import os

# Adiciona o diretório 'src' ao caminho de busca do Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# Importa os módulos necessários
from gui.main import TelegramScraperGUI
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = TelegramScraperGUI(root)
    root.mainloop()
