# Telegram Scraper

Um aplicativo robusto para extração de mensagens, arquivos e workflows de grupos, canais e tópicos do Telegram.

## Funcionalidades
- Listagem de grupos, canais e tópicos
- Download de mensagens e arquivos anexados (.json, .zip, .rar, etc.)
- Organização dos dados em pastas por grupo/canal/tópico
- Interface gráfica amigável (Tkinter)
- Suporte a raspagem contínua

## Instalação

1. **Clone o repositório:**
   ```bash
   git clone <repo-url>
   cd telegram-scraper/temp-repo
   ```
2. **Crie um ambiente virtual (opcional, mas recomendado):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate    # Windows
   ```
3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuração
Edite o arquivo `config/config.yaml` com suas credenciais do Telegram:
```yaml
telegram:
  api_id: SEU_API_ID
  api_hash: SEU_API_HASH
  phone_number: '+55SEUNUMERO'
  session_file: session.session
scraping:
  channels: []
  continuous_scraping: true
  download_media: true
  interval_seconds: 300
  message_limit: 100
```

## Uso

### Interface Gráfica
Execute o app com:
```bash
python start_app.py
```
Ou:
```bash
python launcher.py
```

- **Conectar ao Telegram:** Clique em "Conectar ao Telegram" e siga as instruções de autenticação.
- **Listar Canais/Grupos:** Clique em "Listar Canais" para ver todos os grupos/canais/tópicos disponíveis.
- **Raspar Canais:** Clique em "Raspar Canais" para iniciar a extração de mensagens e arquivos.
- **Download de Mídia:** Certifique-se de que a opção "Download de Mídia" está ativada para baixar arquivos anexados.

### Estrutura dos Dados
Os dados extraídos serão salvos em pastas organizadas por grupo/canal/tópico, dentro de `scraped_data/`.

## Observações
- O app baixa automaticamente arquivos `.json`, `.zip`, `.rar` e outros documentos anexados às mensagens.
- O nome dos arquivos e pastas é sanitizado para evitar problemas com caracteres especiais.
- Logs detalhados são salvos em `gui.log` e `system.log`.

## Licença
MIT 