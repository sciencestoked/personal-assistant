# Deployment Guide for Linux Server

This guide will help you deploy the Personal Assistant on your home Linux server.

## Server Requirements

- Linux server (Ubuntu/Debian recommended)
- Python 3.11 or higher
- 8GB RAM (minimum)
- 500GB SSD storage
- Intel i5 or equivalent CPU
- Internet connection

## Deployment Steps

### 1. Transfer Repository to Server

From your Mac development machine:

```bash
# Option 1: Push to GitHub and clone on server
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo>
git push -u origin main

# Then on your Linux server:
git clone <your-github-repo>
cd personal_assistant
```

**OR**

```bash
# Option 2: Direct transfer via SCP
cd /Users/s-singhal
tar czf personal_assistant.tar.gz personal_assistant/
scp personal_assistant.tar.gz user@your-server-ip:/home/user/

# Then on your Linux server:
tar xzf personal_assistant.tar.gz
cd personal_assistant
```

### 2. Server Setup

SSH into your Linux server:

```bash
ssh user@your-server-ip
cd personal_assistant
```

Install system dependencies:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 (if not already installed)
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Ollama (for local LLM)
curl https://ollama.ai/install.sh | sh

# Pull the LLM model
ollama pull llama3.1:8b
```

### 3. Python Environment Setup

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env  # or vim .env
```

Update the configuration:

```bash
# LLM Configuration - Use Ollama for local
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434

# OR use Groq for free cloud API
# LLM_PROVIDER=groq
# GROQ_API_KEY=your_groq_api_key_here

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Database
DATABASE_URL=sqlite:///data/assistant.db

# Add your Google Calendar, Notion, and Email credentials
# (See README.md for setup instructions)
```

### 5. Create Systemd Service

Create a systemd service file to run the assistant as a background service:

```bash
sudo nano /etc/systemd/system/personal-assistant.service
```

Add the following content (adjust paths as needed):

```ini
[Unit]
Description=Personal Assistant API Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/personal_assistant
Environment="PATH=/home/your-username/personal_assistant/venv/bin"
ExecStart=/home/your-username/personal_assistant/venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Replace** `your-username` with your actual Linux username.

Enable and start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable personal-assistant

# Start the service
sudo systemctl start personal-assistant

# Check status
sudo systemctl status personal-assistant
```

### 6. Set Up Scheduled Tasks (Cron)

Add cron jobs for automatic daily briefings and evening summaries:

```bash
crontab -e
```

Add these lines (adjust paths):

```bash
# Daily briefing at 8:00 AM
0 8 * * * cd /home/your-username/personal_assistant && /home/your-username/personal_assistant/venv/bin/python -m src.cli briefing >> /home/your-username/personal_assistant/data/briefing.log 2>&1

# Evening summary at 8:00 PM
0 20 * * * cd /home/your-username/personal_assistant && /home/your-username/personal_assistant/venv/bin/python -m src.cli summary >> /home/your-username/personal_assistant/data/summary.log 2>&1
```

### 7. Configure Firewall

If you want to access the web interface from other devices on your network:

```bash
# Allow port 8000
sudo ufw allow 8000/tcp

# Check firewall status
sudo ufw status
```

### 8. Set Up Reverse Proxy (Optional)

For production use, set up Nginx as a reverse proxy:

```bash
# Install Nginx
sudo apt install nginx -y

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/personal-assistant
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name your-server-ip;  # or your domain name

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/personal-assistant /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

## Accessing the Assistant

### From Local Network

- Web Interface: `http://your-server-ip:8000`
- API: `http://your-server-ip:8000/api/`

### From Server Terminal

```bash
# Activate virtual environment
cd ~/personal_assistant
source venv/bin/activate

# Run CLI commands
python -m src.cli briefing
python -m src.cli priorities
python -m src.cli ask "What's on my schedule today?"
```

## Monitoring and Maintenance

### View Logs

```bash
# Service logs
sudo journalctl -u personal-assistant -f

# Cron job logs
tail -f ~/personal_assistant/data/briefing.log
tail -f ~/personal_assistant/data/summary.log
```

### Restart Service

```bash
sudo systemctl restart personal-assistant
```

### Update Application

```bash
cd ~/personal_assistant
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart personal-assistant
```

### Check Resource Usage

```bash
# Check memory usage
free -h

# Check disk usage
df -h

# Check CPU usage
top

# Check if Ollama is running (if using local LLM)
ollama list
```

## Optimization Tips

### For 8GB RAM Server

If using local Ollama:
- Use smaller models: `llama3.1:8b` (uses ~4-6GB RAM)
- Limit concurrent requests
- Monitor memory usage

**OR** switch to cloud API (Groq free tier):

```bash
# In .env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-70b-versatile
```

This uses <100MB RAM and is faster!

### Database Maintenance

The SQLite database is lightweight, but you can optimize it:

```bash
# Backup database
cp data/assistant.db data/assistant.db.backup

# Vacuum database (optional, reduces size)
sqlite3 data/assistant.db "VACUUM;"
```

## Security Considerations

1. **Firewall**: Only expose port 8000 to your local network
2. **Credentials**: Keep `.env` file secure (chmod 600)
3. **HTTPS**: Use Nginx with Let's Encrypt for SSL if exposing to internet
4. **Updates**: Keep system and Python packages updated
5. **Backups**: Regularly backup your data and config directories

```bash
# Secure .env file
chmod 600 .env

# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/your-username/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
tar czf $BACKUP_DIR/assistant_backup_$DATE.tar.gz \
  data/ config/ .env
# Keep only last 7 backups
ls -t $BACKUP_DIR/assistant_backup_*.tar.gz | tail -n +8 | xargs -r rm
EOF

chmod +x backup.sh

# Add to cron (daily backup at 2 AM)
crontab -e
# Add: 0 2 * * * /home/your-username/personal_assistant/backup.sh
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u personal-assistant -n 50

# Check if port is already in use
sudo lsof -i :8000

# Verify Python environment
source venv/bin/activate
python -m src.cli config
```

### Ollama Not Working

```bash
# Check if Ollama is running
systemctl status ollama

# Start Ollama
sudo systemctl start ollama

# Test Ollama
ollama run llama3.1:8b "Hello"
```

### Calendar/Notion/Email Not Working

- Check credentials in `.env`
- Verify internet connectivity
- Check logs for specific error messages

## Performance Benchmarks

On i5 + 8GB RAM:

| LLM Provider | Response Time | RAM Usage | Cost |
|--------------|--------------|-----------|------|
| Ollama (local) | 2-5s | 4-6 GB | Free |
| Groq | 0.5-1s | <100 MB | Free tier |
| OpenAI | 0.5-1s | <100 MB | $5-20/mo |
| Claude | 0.5-1s | <100 MB | $3-15/mo |

**Recommendation**: Use Groq for best performance on limited hardware!

## Support

For issues or questions:
1. Check logs: `sudo journalctl -u personal-assistant -f`
2. Review configuration: `python -m src.cli config`
3. Consult README.md for setup details
4. Check GitHub issues

## Next Steps

After deployment:
1. Test all features via web interface
2. Set up integrations (Calendar, Notion, Email)
3. Customize cron schedules for briefings
4. Monitor resource usage
5. Set up backups

Your personal assistant is now running 24/7 on your home server!
