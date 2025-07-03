import sys
import os

# Adiciona o diretório raiz do projeto ao caminho de busca do Python
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(project_root)

# Adiciona explicitamente o diretório 'src' ao caminho de busca
src_dir = os.path.join(project_root, "src")
sys.path.append(src_dir)

import tkinter as tk
from gui.main import TelegramScraperGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = TelegramScraperGUI(root)
    root.mainloop()
