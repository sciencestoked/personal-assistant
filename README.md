# Personal Assistant

An intelligent personal assistant that runs on your home server, integrating with Google Calendar, Notion, and Email to help you automate your daily life.

## Features

- **Smart Daily Briefings**: Morning summaries of your day with calendar events, important emails, and notes
- **Evening Summaries**: End-of-day recaps and preparation for tomorrow
- **Task Prioritization**: AI-powered analysis of your tasks to suggest what to focus on
- **Email Processing**: Automatic extraction of tasks and action items from emails
- **Context-Aware Q&A**: Ask questions about your schedule, notes, and emails
- **Next Action Suggestions**: Get intelligent suggestions for what to do next
- **Multiple Interfaces**: Web UI, REST API, and CLI
- **Flexible LLM Support**: Choose between local (Ollama) or cloud (OpenAI, Claude, Groq) models

## Architecture

```
personal_assistant/
├── src/
│   ├── api/              # FastAPI web server
│   ├── core/             # Core business logic & assistant
│   ├── integrations/     # Calendar, Notion, Email integrations
│   ├── llm/              # LLM provider abstraction
│   └── cli.py            # Command-line interface
├── config/               # Configuration files
├── data/                 # Database and logs
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables
```

## Prerequisites

- Python 3.11 or higher
- Google Calendar API credentials (optional)
- Notion API key (optional)
- Email account with IMAP access (optional)
- Ollama installed (for local LLM) OR API keys for cloud providers

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd personal_assistant
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Choose your LLM provider
LLM_PROVIDER=ollama  # or openai, anthropic, groq

# For Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b

# For cloud providers (optional)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GROQ_API_KEY=your_key_here

# Google Calendar (optional)
GOOGLE_CREDENTIALS_PATH=config/google_credentials.json
GOOGLE_TOKEN_PATH=config/google_token.json

# Notion (optional)
NOTION_API_KEY=your_notion_key_here
NOTION_DATABASE_ID=your_database_id_here

# Email (optional)
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password_here
```

### 5. Set Up Integrations

#### Google Calendar

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials JSON and save as `config/google_credentials.json`
6. Run the app - it will open a browser for authentication

#### Notion

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create a new integration
3. Copy the API key to your `.env` file
4. Share your Notion database with the integration
5. Copy the database ID to your `.env` file

#### Email (Gmail)

1. Enable 2-factor authentication on your Gmail account
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Use the app password in your `.env` file

### 6. Install Ollama (Optional, for Local LLM)

If using local LLM:

```bash
# On Mac
brew install ollama

# On Linux
curl https://ollama.ai/install.sh | sh

# Pull the model
ollama pull llama3.1:8b
```

## Usage

### CLI Interface

The CLI provides quick access to all assistant features:

```bash
# Get daily briefing
python -m src.cli briefing

# Get evening summary
python -m src.cli summary

# Get task priorities
python -m src.cli priorities

# Get next action suggestion
python -m src.cli next

# Ask a question
python -m src.cli ask "What's on my calendar today?"

# Ask without context
python -m src.cli ask "What is Python?" --no-context

# Start web server
python -m src.cli server

# Show configuration
python -m src.cli config

# Show version
python -m src.cli version
```

### Web Interface

Start the web server:

```bash
python -m src.cli server
```

Then open your browser to `http://localhost:8000`

The web interface provides:
- Daily briefings
- Evening summaries
- Task prioritization
- Next action suggestions
- Question & answer interface

### REST API

The API is available at `http://localhost:8000` with the following endpoints:

- `GET /health` - Health check
- `GET /api/briefing` - Get daily briefing
- `GET /api/evening-summary` - Get evening summary
- `GET /api/priorities` - Get task priorities
- `GET /api/next-action` - Get next action suggestion
- `POST /api/ask` - Ask a question

Example API call:

```bash
# Get daily briefing
curl http://localhost:8000/api/briefing

# Ask a question
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What meetings do I have today?", "include_context": true}'
```

## Running as a Service

See [DEPLOYMENT.md](DEPLOYMENT.md) for instructions on:
- Setting up systemd service on Linux
- Configuring scheduled tasks for daily briefings
- Running on your home server
- Security best practices

## LLM Provider Comparison

| Provider | Cost | Speed | Quality | RAM Usage |
|----------|------|-------|---------|-----------|
| Ollama (Local) | Free | Slow (2-5s) | Good | 4-8 GB |
| Groq | Free tier | Very Fast (<1s) | Excellent | <100 MB |
| OpenAI | ~$5-20/mo | Fast (<1s) | Excellent | <100 MB |
| Claude | ~$3-15/mo | Fast (<1s) | Excellent | <100 MB |

**Recommendation**: Start with Groq (free tier) or Ollama (local), then upgrade to Claude/OpenAI if needed.

## Project Structure

- `src/api/main.py` - FastAPI server and web interface
- `src/cli.py` - Command-line interface
- `src/core/assistant.py` - Main assistant logic
- `src/core/context_builder.py` - Aggregates data from all sources
- `src/core/config.py` - Configuration management
- `src/integrations/` - Google Calendar, Notion, Email integrations
- `src/llm/` - LLM provider abstraction layer

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

The assistant follows a modular architecture:

1. **Integrations Layer**: Connects to external services
2. **Context Builder**: Aggregates data from all sources
3. **LLM Layer**: Provides abstraction over different LLM providers
4. **Assistant Core**: Implements intelligent decision-making
5. **Interface Layer**: Provides CLI, API, and Web access

## Troubleshooting

### Google Calendar Authentication

If you get authentication errors:
1. Delete `config/google_token.json`
2. Run the app again - it will re-authenticate
3. Make sure you've enabled the Calendar API in Google Cloud Console

### Ollama Connection Issues

If Ollama isn't connecting:
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve
```

### Email Connection Issues

For Gmail:
- Use an App Password, not your regular password
- Enable IMAP in Gmail settings
- Check firewall settings

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built with FastAPI, LangChain, and rich CLI
- Supports multiple LLM providers: Ollama, OpenAI, Anthropic, Groq
- Integrations: Google Calendar, Notion, Email (IMAP)
