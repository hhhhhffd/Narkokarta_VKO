#!/bin/bash

# Скрипт для запуска в режиме разработки с ngrok

set -e

echo "🚀 Запуск Наркокарты в режиме разработки..."
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка наличия ngrok
if ! command -v ngrok &> /dev/null; then
    echo -e "${RED}❌ ngrok не установлен${NC}"
    echo ""
    echo "Установите ngrok:"
    echo ""
    echo "macOS:"
    echo "  brew install ngrok"
    echo ""
    echo "Linux:"
    echo "  wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"
    echo "  tar -xvf ngrok-v3-stable-linux-amd64.tgz"
    echo "  sudo mv ngrok /usr/local/bin/"
    echo ""
    echo "Windows:"
    echo "  scoop install ngrok"
    echo "  или скачайте с https://ngrok.com/download"
    echo ""
    exit 1
fi

# Проверка .env файла
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Файл .env не найден, создаём из .env.example${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Создан файл .env${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Не забудьте установить TELEGRAM_BOT_TOKEN в .env файле!${NC}"
    echo ""
fi

# Загружаем переменные из .env
if [ -f .env ]; then
    set -a
    source <(cat .env | grep -v '^#' | grep -v '^\[' | grep -v '^\]' | grep '=' | sed 's/\r$//')
    set +a
fi

# Проверка TELEGRAM_BOT_TOKEN
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "your-bot-token-from-botfather" ]; then
    echo -e "${RED}❌ TELEGRAM_BOT_TOKEN не установлен в .env${NC}"
    echo ""
    echo "1. Получите токен у @BotFather в Telegram"
    echo "2. Добавьте в .env файл:"
    echo "   TELEGRAM_BOT_TOKEN=your-actual-token-here"
    echo ""
    exit 1
fi

# Создаём директории если нужно
mkdir -p logs
mkdir -p uploads

echo -e "${BLUE}📦 Шаг 1/4: Проверка зависимостей...${NC}"
# Проверяем наличие venv
if [ ! -d ".venv" ]; then
    echo "Создаём виртуальное окружение..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

echo -e "${GREEN}✅ Зависимости готовы${NC}"
echo ""

echo -e "${BLUE}🌐 Шаг 2/4: Запуск ngrok туннеля...${NC}"
# Запускаем ngrok в фоне
ngrok http 8000 > /dev/null &
NGROK_PID=$!

# Ждём пока ngrok запустится
sleep 3

# Получаем публичный URL от ngrok
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*ngrok[^"]*' | head -1)

if [ -z "$NGROK_URL" ]; then
    echo -e "${RED}❌ Не удалось получить URL от ngrok${NC}"
    kill $NGROK_PID 2>/dev/null
    exit 1
fi

echo -e "${GREEN}✅ Ngrok запущен: $NGROK_URL${NC}"
echo ""

# Обновляем WEBAPP_URL
export WEBAPP_URL="$NGROK_URL/web/index.html"
export API_BASE_URL="$NGROK_URL"

echo -e "${BLUE}🖥️  Шаг 3/4: Запуск API сервера...${NC}"
# Запускаем uvicorn в фоне
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &
API_PID=$!

# Ждём пока сервер запустится
sleep 3

# Проверяем что сервер запущен
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}❌ API сервер не запустился${NC}"
    kill $NGROK_PID 2>/dev/null
    kill $API_PID 2>/dev/null
    exit 1
fi

echo -e "${GREEN}✅ API сервер запущен${NC}"
echo ""

echo -e "${BLUE}🤖 Шаг 4/4: Запуск Telegram бота...${NC}"
# Запускаем бота в фоне
python telegram_bot.py > logs/bot.log 2>&1 &
BOT_PID=$!

sleep 2

echo -e "${GREEN}✅ Telegram бот запущен${NC}"
echo ""

# Сохраняем PIDs для остановки
echo $NGROK_PID > .ngrok.pid
echo $API_PID > .api.pid
echo $BOT_PID > .bot.pid

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✨ Всё готово! Наркокарта запущена${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${BLUE}📍 Ссылки:${NC}"
echo "   • Ngrok URL:    $NGROK_URL"
echo "   • WebApp URL:   $WEBAPP_URL"
echo "   • API Docs:     $NGROK_URL/docs"
echo "   • Ngrok UI:     http://localhost:4040"
echo ""
echo -e "${BLUE}📊 Логи:${NC}"
echo "   • API:          tail -f logs/api.log"
echo "   • Bot:          tail -f logs/bot.log"
echo ""
echo -e "${BLUE}🤖 Telegram:${NC}"
echo "   Откройте вашего бота и нажмите:"
echo -e "   ${GREEN}🗺 Открыть карту${NC}"
echo ""
echo -e "${YELLOW}⚠️  Важно:${NC}"
echo "   • Ngrok URL меняется при каждом запуске"
echo "   • Для остановки используйте: ./stop_dev.sh"
echo "   • Или нажмите Ctrl+C"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Нажмите Ctrl+C для остановки..."

# Функция для очистки при выходе
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Остановка сервисов...${NC}"

    if [ -f .ngrok.pid ]; then
        kill $(cat .ngrok.pid) 2>/dev/null
        rm .ngrok.pid
    fi

    if [ -f .api.pid ]; then
        kill $(cat .api.pid) 2>/dev/null
        rm .api.pid
    fi

    if [ -f .bot.pid ]; then
        kill $(cat .bot.pid) 2>/dev/null
        rm .bot.pid
    fi

    echo -e "${GREEN}✅ Все сервисы остановлены${NC}"
    exit 0
}

# Ловим сигнал прерывания
trap cleanup INT TERM

# Ждём в фоне
wait
