# ChemAgent Deployment Guide

Complete guide for deploying ChemAgent in various environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Configuration](#configuration)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Security](#security)
9. [Scaling](#scaling)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 10 GB
- OS: Linux, macOS, or Windows

**Recommended:**
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 20+ GB SSD
- OS: Linux (Ubuntu 20.04+)

### Software Dependencies

- Python 3.10-3.12
- pip or conda
- Docker (for containerized deployment)
- Git
- PostgreSQL or Redis (optional, for caching)

---

## Local Development

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/chemagent.git
cd chemagent
```

### 2. Create Environment

**Option A: Conda (Recommended)**
```bash
conda env create -f environment.yml
conda activate chemagent
```

**Option B: venv**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
nano .env
```

### 4. Run Services

**Web UI:**
```bash
python -m chemagent.ui.run
# Access at http://localhost:7860
```

**API Server:**
```bash
uvicorn chemagent.api.server:app --reload
# Access at http://localhost:8000
```

**CLI:**
```bash
python -m chemagent.cli
```

---

## Docker Deployment

### Quick Start (Development)

```bash
# Build and run
docker-compose -f docker-compose.dev.yml up

# Access services:
# - API: http://localhost:8000
# - Web UI: http://localhost:7860
# - Docs: http://localhost:8000/docs
```

### Production Build

```bash
# Build production image
docker build -t chemagent:latest .

# Run with docker-compose
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f
```

### Multi-Service Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  chemagent-api:
    image: chemagent:latest
    ports:
      - "8000:8000"
    environment:
      - CHEMAGENT_WORKERS=4
      - CHEMAGENT_CACHE_ENABLED=true
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  chemagent-ui:
    image: chemagent:latest
    command: python -m chemagent.ui.run --host 0.0.0.0
    ports:
      - "7860:7860"
    environment:
      - CHEMAGENT_API_URL=http://chemagent-api:8000
    depends_on:
      - chemagent-api
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

---

## Production Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3-pip git nginx certbot

# Create application user
sudo useradd -m -s /bin/bash chemagent
sudo su - chemagent
```

### 2. Application Installation

```bash
# Clone repository
git clone https://github.com/yourusername/chemagent.git
cd chemagent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn uvicorn[standard]
```

### 3. Configure Systemd Service

**API Service:**
```ini
# /etc/systemd/system/chemagent-api.service
[Unit]
Description=ChemAgent API Service
After=network.target

[Service]
Type=exec
User=chemagent
Group=chemagent
WorkingDirectory=/home/chemagent/chemagent
Environment="PATH=/home/chemagent/chemagent/venv/bin"
EnvironmentFile=/home/chemagent/chemagent/.env
ExecStart=/home/chemagent/chemagent/venv/bin/uvicorn chemagent.api.server:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**UI Service:**
```ini
# /etc/systemd/system/chemagent-ui.service
[Unit]
Description=ChemAgent Web UI
After=network.target chemagent-api.service

[Service]
Type=exec
User=chemagent
Group=chemagent
WorkingDirectory=/home/chemagent/chemagent
Environment="PATH=/home/chemagent/chemagent/venv/bin"
EnvironmentFile=/home/chemagent/chemagent/.env
ExecStart=/home/chemagent/chemagent/venv/bin/python -m chemagent.ui.run --host 0.0.0.0 --port 7860
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start services:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable chemagent-api chemagent-ui
sudo systemctl start chemagent-api chemagent-ui
sudo systemctl status chemagent-api chemagent-ui
```

### 4. Nginx Configuration

```nginx
# /etc/nginx/sites-available/chemagent
server {
    listen 80;
    server_name chemagent.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name chemagent.example.com;
    
    ssl_certificate /etc/letsencrypt/live/chemagent.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chemagent.example.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # Streaming endpoint
    location /api/query/stream {
        proxy_pass http://127.0.0.1:8000/query/stream;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
    
    # Web UI
    location / {
        proxy_pass http://127.0.0.1:7860/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for Gradio
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Static files (if any)
    location /static/ {
        alias /home/chemagent/chemagent/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**Enable configuration:**
```bash
sudo ln -s /etc/nginx/sites-available/chemagent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. SSL Certificate

```bash
sudo certbot --nginx -d chemagent.example.com
sudo systemctl reload nginx
```

---

## Cloud Deployment

### AWS Deployment

**1. EC2 Instance:**
- Instance type: t3.medium (2 vCPU, 4 GB RAM)
- AMI: Ubuntu Server 22.04 LTS
- Storage: 20 GB GP3
- Security group: Allow 80, 443, 8000

**2. Setup Script:**
```bash
#!/bin/bash
# EC2 user data script

# Install dependencies
apt update && apt upgrade -y
apt install -y python3.10 python3-pip git nginx

# Install ChemAgent
cd /opt
git clone https://github.com/yourusername/chemagent.git
cd chemagent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env as needed

# Setup systemd services (as shown above)
# Configure nginx (as shown above)
```

**3. Using Docker on AWS ECS:**
```bash
# Build and push image
docker build -t chemagent:latest .
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag chemagent:latest <account>.dkr.ecr.us-east-1.amazonaws.com/chemagent:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/chemagent:latest

# Create ECS task definition and service
# (Use AWS Console or CLI)
```

### Google Cloud Platform

**1. Cloud Run:**
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/chemagent
gcloud run deploy chemagent \
  --image gcr.io/PROJECT_ID/chemagent \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --port 8000
```

### Azure

**1. Container Instances:**
```bash
# Build and push image
docker build -t chemagent:latest .
az acr login --name myregistry
docker tag chemagent:latest myregistry.azurecr.io/chemagent:latest
docker push myregistry.azurecr.io/chemagent:latest

# Deploy container
az container create \
  --resource-group myResourceGroup \
  --name chemagent \
  --image myregistry.azurecr.io/chemagent:latest \
  --cpu 2 \
  --memory 4 \
  --port 8000 7860 \
  --environment-variables CHEMAGENT_WORKERS=4
```

---

## Configuration

### Environment Variables

Complete list of configuration options:

```bash
# Server Configuration
CHEMAGENT_HOST=0.0.0.0
CHEMAGENT_PORT=8000
CHEMAGENT_WORKERS=4

# Parallel Execution
CHEMAGENT_ENABLE_PARALLEL=true
CHEMAGENT_MAX_WORKERS=4

# Caching
CHEMAGENT_CACHE_ENABLED=true
CHEMAGENT_CACHE_TTL=3600
CHEMAGENT_CACHE_BACKEND=memory  # or redis
REDIS_URL=redis://localhost:6379

# Logging
CHEMAGENT_LOG_LEVEL=INFO
CHEMAGENT_LOG_FILE=logs/chemagent.log

# Security
CHEMAGENT_ENABLE_AUTH=false
CHEMAGENT_API_KEY=your-secret-key
CHEMAGENT_RATE_LIMIT_PER_MINUTE=60

# Features
CHEMAGENT_ENABLE_STREAMING=true
CHEMAGENT_ENABLE_METRICS=true

# Database (optional)
DATABASE_URL=postgresql://user:pass@localhost/chemagent
```

### Production Settings

```bash
# .env.production
CHEMAGENT_HOST=0.0.0.0
CHEMAGENT_PORT=8000
CHEMAGENT_WORKERS=8
CHEMAGENT_MAX_WORKERS=16
CHEMAGENT_CACHE_ENABLED=true
CHEMAGENT_CACHE_BACKEND=redis
REDIS_URL=redis://redis:6379
CHEMAGENT_LOG_LEVEL=WARNING
CHEMAGENT_ENABLE_AUTH=true
CHEMAGENT_API_KEY=<your-secure-api-key>
CHEMAGENT_RATE_LIMIT_PER_MINUTE=120
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Service status
systemctl status chemagent-api
systemctl status chemagent-ui

# Logs
journalctl -u chemagent-api -f
journalctl -u chemagent-ui -f
```

### Metrics

**Prometheus Integration:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'chemagent'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Log Rotation

```bash
# /etc/logrotate.d/chemagent
/home/chemagent/chemagent/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 chemagent chemagent
    sharedscripts
    postrotate
        systemctl reload chemagent-api chemagent-ui
    endscript
}
```

### Backups

```bash
#!/bin/bash
# backup.sh - Daily backup script

BACKUP_DIR=/backups/chemagent/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Backup data
tar -czf $BACKUP_DIR/data.tar.gz /home/chemagent/chemagent/data

# Backup configuration
cp /home/chemagent/chemagent/.env $BACKUP_DIR/

# Backup database (if using)
pg_dump chemagent > $BACKUP_DIR/database.sql

# Remove old backups (keep 30 days)
find /backups/chemagent -mtime +30 -delete

# Add to crontab:
# 0 2 * * * /home/chemagent/backup.sh
```

---

## Security

### Best Practices

1. **Always use HTTPS** in production
2. **Enable authentication** for API access
3. **Use strong API keys** (generate with `openssl rand -hex 32`)
4. **Implement rate limiting**
5. **Keep dependencies updated**
6. **Use firewall** (UFW, iptables, or cloud security groups)
7. **Regular security audits**

### Firewall Configuration

```bash
# UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### API Key Authentication

```python
# config.py
CHEMAGENT_ENABLE_AUTH=true
CHEMAGENT_API_KEY=your-secure-api-key

# Usage
curl -H "X-API-Key: your-secure-api-key" http://localhost:8000/query
```

---

## Scaling

### Horizontal Scaling

**Load Balancer Configuration (nginx):**
```nginx
upstream chemagent_backend {
    least_conn;
    server 10.0.1.1:8000;
    server 10.0.1.2:8000;
    server 10.0.1.3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://chemagent_backend;
    }
}
```

### Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chemagent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chemagent
  template:
    metadata:
      labels:
        app: chemagent
    spec:
      containers:
      - name: chemagent
        image: chemagent:latest
        ports:
        - containerPort: 8000
        env:
        - name: CHEMAGENT_WORKERS
          value: "4"
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: chemagent-service
spec:
  selector:
    app: chemagent
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## Troubleshooting

### Common Issues

**1. Port already in use:**
```bash
# Find process
sudo lsof -i :8000
# Kill process
kill -9 <PID>
# Or use different port
CHEMAGENT_PORT=8001 uvicorn chemagent.api.server:app
```

**2. Permission denied:**
```bash
# Fix ownership
sudo chown -R chemagent:chemagent /home/chemagent/chemagent
# Fix permissions
chmod 755 /home/chemagent/chemagent
```

**3. Module not found:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
# Reinstall dependencies
pip install -r requirements.txt
```

**4. High memory usage:**
```bash
# Reduce workers
CHEMAGENT_WORKERS=2 uvicorn chemagent.api.server:app
# Enable worker recycling
uvicorn chemagent.api.server:app --workers 4 --limit-concurrency 100
```

**5. Slow response times:**
- Enable caching: `CHEMAGENT_CACHE_ENABLED=true`
- Use Redis: `CHEMAGENT_CACHE_BACKEND=redis`
- Increase workers: `CHEMAGENT_WORKERS=8`
- Enable parallel execution: `CHEMAGENT_ENABLE_PARALLEL=true`

### Debug Mode

```bash
# Enable debug logging
export CHEMAGENT_LOG_LEVEL=DEBUG
python -m chemagent.cli --verbose "your query"

# Check logs
tail -f logs/chemagent.log

# Test API endpoints
curl -X GET http://localhost:8000/health
curl -X GET http://localhost:8000/config
```

---

## Maintenance

### Updates

```bash
# Pull latest code
cd /home/chemagent/chemagent
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart services
sudo systemctl restart chemagent-api chemagent-ui
```

### Database Migrations

```bash
# Run migrations (if using database)
alembic upgrade head
```

### Performance Tuning

```bash
# Monitor performance
htop
iotop
netstat -tulpn

# Check API performance
ab -n 1000 -c 10 http://localhost:8000/health
```

---

## Support

For deployment issues:
- GitHub: https://github.com/yourusername/chemagent/issues
- Email: support@example.com
- Docs: https://chemagent.readthedocs.io

**Production Support:** enterprise@example.com
