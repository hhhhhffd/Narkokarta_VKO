#!/bin/bash

# Скрипт для остановки dev окружения

echo "🛑 Остановка Наркокарты..."

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Останавливаем ngrok
if [ -f .ngrok.pid ]; then
    kill $(cat .ngrok.pid) 2>/dev/null
    rm .ngrok.pid
    echo -e "${GREEN}✅ Ngrok остановлен${NC}"
fi

# Останавливаем API
if [ -f .api.pid ]; then
    kill $(cat .api.pid) 2>/dev/null
    rm .api.pid
    echo -e "${GREEN}✅ API сервер остановлен${NC}"
fi

# Останавливаем бота
if [ -f .bot.pid ]; then
    kill $(cat .bot.pid) 2>/dev/null
    rm .bot.pid
    echo -e "${GREEN}✅ Telegram бот остановлен${NC}"
fi

# Убиваем оставшиеся процессы на всякий случай
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "telegram_bot.py" 2>/dev/null
pkill -f "ngrok http 8000" 2>/dev/null

echo ""
echo -e "${GREEN}✨ Все сервисы остановлены${NC}"
