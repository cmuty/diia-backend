# 🚀 Deploy DiiaBackend на Render

## 📋 Що буде на Render

✅ Telegram бот з webhook  
✅ API для iOS приложения  
✅ База данных SQLite  
✅ Система платежей CryptoPay  

---

## 🎯 Крок 1: Підготовка на Render.com

### 1. Створи аккаунт
1. Зайди на [render.com](https://render.com)
2. Sign up (можна через GitHub)
3. Підтверди email

### 2. Створи новий Web Service

1. **Dashboard** → **New +** → **Web Service**
2. Підключи GitHub репозиторій
3. Налаштування:
   ```
   Name: diia-backend
   Region: Frankfurt (EU)
   Branch: main
   Root Directory: DiiaBackend
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python render_server.py
   ```

---

## ⚙️ Крок 2: Environment Variables

Додай у **Environment** секцію:

```bash
BOT_TOKEN=твій_токен_бота
DATABASE_PATH=database/diia.db
PORT=10000
ADMIN_IDS=448592121
CRYPTOPAY_TOKEN=479115:AARxfBgUT3h1n9oBCwY1Y3UbgwN1n6S9mHn
```

**Як знайти BOT_TOKEN:**
1. Відкрий Telegram
2. Знайди [@BotFather](https://t.me/BotFather)
3. Надішли `/mybots`
4. Обери свого бота
5. Обери "API Token"

---

## 📤 Крок 3: Deploy

1. Натисни **Create Web Service**
2. Дочекайся білду (3-5 хвилин)
3. Сервер буде доступний за адресою:
   ```
   https://diia-backend-xxxx.onrender.com
   ```

---

## 🔗 Крок 4: Налаштування Webhook

Після деплою потрібно налаштувати webhook для Telegram бота.

### Варіант 1: Через curl

```bash
curl -X POST https://diia-backend-xxxx.onrender.com/set_webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://diia-backend-xxxx.onrender.com/webhook"}'
```

### Варіант 2: Через Python скрипт

Створи файл `set_webhook.py`:

```python
import requests

WEBHOOK_URL = "https://diia-backend-xxxx.onrender.com/webhook"

response = requests.post(
    f"{WEBHOOK_URL.rsplit('/', 1)[0]}/set_webhook",
    json={"url": WEBHOOK_URL}
)

print(response.json())
```

Запусти:
```bash
python set_webhook.py
```

### Варіант 3: Через Telegram API

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://diia-backend-xxxx.onrender.com/webhook"}'
```

**Заміни `<BOT_TOKEN>` на свій токен!**

---

## ✅ Крок 5: Перевірка

### 1. Перевір Health Check

Відкрий в браузері:
```
https://diia-backend-xxxx.onrender.com/api/health
```

Має відповісти:
```json
{"status": "ok", "message": "Render server is running"}
```

### 2. Перевір Webhook

Відкрий:
```
https://diia-backend-xxxx.onrender.com/webhook
```

Має відповісти `{"ok": true}` або помилку (це нормально без POST запиту)

### 3. Перевір Бота

Надішли `/start` боту в Telegram. Якщо бот відповів - все працює! ✅

---

## 📱 Оновлення iOS App

Онови URL в `NetworkManager.swift`:

```swift
// Замінити
private let baseURL = "https://962a16b88968.ngrok-free.app"

// На
private let baseURL = "https://diia-backend-xxxx.onrender.com"
```

---

## 🔧 Troubleshooting

### "Internal Server Error"

1. Перевір **Logs** в Render Dashboard
2. Перевір чи всі environment variables встановлені
3. Перевір чи BOT_TOKEN правильний

### "Webhook not set"

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

Перевір поточний webhook.

### "Service is sleeping"

**Render Free Tier** засинає після 15 хвилин неактивності.

**Рішення:**
1. Upgrade до платного плану
2. Використовуй Keep-Alive сервіс (cron-job.org)
3. Додай моніторинг для продовження активності

### Keep-Alive скрипт

Створи окремий endpoint:

```python
@flask_app.route("/keep-alive")
def keep_alive():
    return jsonify({"status": "ok"})
```

Додай у cron-job.org:
- URL: `https://diia-backend-xxxx.onrender.com/keep-alive`
- Frequency: кожні 10 хвилин

---

## 💰 Pricing

### Free Tier:
- ✅ 512 MB RAM
- ✅ 0.1 CPU
- ⏰ Sleeps after 15 min inactivity
- 🆓 $0/month

### Starter ($7/month):
- ✅ 512 MB RAM
- ✅ 0.5 CPU
- ✅ Always on
- ✅ Auto-deploy from GitHub

---

## 📊 Monitoring

### Logs
Render Dashboard → Your Service → **Logs**

### Metrics
- CPU usage
- Memory usage
- Response time
- Request count

---

## 🔄 Auto-Deploy

Render автоматично деплоїть при:
- ✅ Push в main branch
- ✅ Merge Pull Request
- ✅ Зміна в `requirements.txt`

---

## 🎉 Готово!

Тепер твій бот працює 24/7 на Render без ngrok! 🚀

**Переваги Render:**
- ✅ Безкоштовний план
- ✅ HTTPS out of the box
- ✅ Auto-deploy
- ✅ Environment variables
- ✅ Logs та monitoring
- ✅ No ngrok needed!
