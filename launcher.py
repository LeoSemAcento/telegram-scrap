import sys
import os
import tkinter as tk

# Adiciona o diretório 'src' ao sys.path para que as importações funcionem
# quando o script é executado diretamente.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from gui.main import TelegramScraperGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = TelegramScraperGUI(root)
    root.mainloop()
