# Inventory Tracker Chatbot

Chatbot system for inventory management using **MySQL**, **API**, and **n8n**.

## 🚀 Features

- 📊 Inventory Management – Products, categories, stock-in, sales, profitability reports
- 🤖 Chatbot Automation – n8n workflows connect user input to API/DB actions

## 🚀 Services
- **db** → MySQL 8.4 (UTF-8, seeded with `init.sql`)  
- **api** → FastAPI  
- **n8n** → workflow automation & chatbot logic  

## ⚙️ Setup
```bash
#Start
docker compose up -d --build
#Stop using
docker compose down
```
After that import Chatbot.json in workflow folder to blank n8n workflow

## Create a .env file (used by n8n):
```bash
GENERIC_TIMEZONE=Asia/Bangkok
IM_URL = http://api:8000
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=supersecret
```

## 🔌 Access
- MySQL → `localhost:3306` (db: `myapp`, user: `root`, pass: `rootpass`)  
- API → [http://localhost:8000](http://localhost:8000)  
- n8n → [http://localhost:5678](http://localhost:5678)  

## 🔧 n8n DB Connection
- **Host**: `db`  
- **Database**: `myapp`  
- **User**: `appuser`  
- **Password**: `apppass`  
- **Port**: `3306`  

