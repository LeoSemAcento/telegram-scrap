import sys
import os

print("Caminho de busca do Python:")
for path in sys.path:
    print(path)

print("\nDiretório atual:")
print(os.getcwd())

print("\nEstrutura de diretórios:")
for root, dirs, files in os.walk(os.path.abspath(os.path.dirname(__file__))):
    print(f"Root: {root}")
    print(f"Dirs: {dirs}")
    print(f"Files: {files}")
    print("---")
