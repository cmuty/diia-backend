# 🐘 PostgreSQL Migration Guide

## ✅ Что сделано:

1. ✅ Добавлены библиотеки `asyncpg` и `psycopg2-binary` в `requirements.txt`
2. ✅ Переписан `database/models.py` с поддержкой PostgreSQL
3. ✅ Обновлён `render.yaml` с `DATABASE_URL`
4. ✅ Обновлены все файлы для использования `DATABASE_URL`
5. ✅ Создан скрипт инициализации `init_db.py`

---

## 🚀 Deployment на Render:

### Шаг 1: Пуш на GitHub

```bash
git add .
git commit -m "МИГРАЦИЯ НА POSTGRESQL: полная поддержка PostgreSQL + SQLite для локальной разработки"
git push origin main
```

### Шаг 2: Deploy на Render

1. Зайди в **Render Dashboard**
2. Открой свой сервис **diia-backend**
3. **Clear build cache & deploy**
4. Дождись завершения деплоя (3-5 минут)

### Шаг 3: Проверка

После деплоя открой:
```
https://diia-backend.onrender.com/api/health
```

Должно вернуть: `{"status":"ok","message":"Server is running"}`

---

## 🔧 Локальная разработка:

### Для SQLite (локально):

Создай `.env` файл:
```env
DATABASE_URL=database/diia.db
BOT_TOKEN=your_bot_token
ADMIN_IDS=your_telegram_id
CRYPTOPAY_TOKEN=your_token
CLOUDINARY_CLOUD_NAME=djoszn8zc
CLOUDINARY_API_KEY=472899494355635
CLOUDINARY_API_SECRET=gGgIhXupY9im376HqlyCwNhZe-c
```

Запусти бота:
```bash
python bot/bot.py
```

### Для PostgreSQL (локально):

В `.env` укажи:
```env
DATABASE_URL=postgresql://postdia_user:kkRbzuUDLdnDvSUym3PvulCHtI815RQq@dpg-d3v8t5hr0fns73c9tq9g-a/postdia
```

Запусти инициализацию:
```bash
python init_db.py
```

---

## 📊 Админ панель:

### Веб админка:

1. Открой `admin/index.html` в браузере
2. Войди (admin / admin123)
3. Увидишь всех пользователей из PostgreSQL

### Консольная админка:

```bash
python admin_panel.py
```

Работает с той БД, которая указана в `DATABASE_URL`.

---

## 🔄 Автоматическое переключение:

Код **автоматически определяет** тип БД по URL:

- **SQLite**: `database/diia.db` или `sqlite:///path/to/db.db`
- **PostgreSQL**: `postgresql://user:pass@host/db`

Никаких изменений в коде не нужно!

---

## 📝 Что изменилось:

### database/models.py
- ✅ Поддержка PostgreSQL и SQLite
- ✅ Connection pooling для PostgreSQL
- ✅ Автоопределение типа БД по URL
- ✅ Все запросы адаптированы под оба движка

### render.yaml
- ✅ `DATABASE_PATH` → `DATABASE_URL`
- ✅ PostgreSQL URL в переменных окружения

### Все файлы (bot.py, render_server.py, api/main.py, admin_panel.py)
- ✅ Используют `DATABASE_URL` вместо `DATABASE_PATH`

---

## ⚠️ Важно:

1. **Данные НЕ мигрируются автоматически**
   - Старая SQLite БД на Render **не используется**
   - PostgreSQL БД **пустая** - нужна новая регистрация через бота

2. **Первый деплой**:
   - Таблицы создаются автоматически при первом запуске
   - Бот заработает сразу после деплоя

3. **Локальная разработка**:
   - SQLite по умолчанию (быстро, удобно)
   - PostgreSQL опционально (если нужно тестировать продакшен)

---

## 🎯 Следующие шаги:

1. ✅ **Пуш на GitHub** (см. выше)
2. ✅ **Deploy на Render** (автоматический)
3. 🔄 **Зарегистрируй пользователей заново** через Telegram бота
4. ✅ **Выдай подписки** через веб админку или консольную

---

## 🆘 Troubleshooting:

### Ошибка: "no module named asyncpg"
```bash
pip install asyncpg psycopg2-binary
```

### Ошибка: "connection refused"
- Проверь что PostgreSQL URL правильный
- Убедись что сервер доступен

### Бот не работает локально:
- Проверь `.env` файл
- Убедись что `DATABASE_URL` указан

### Админ панель не видит пользователей:
- Убедись что API запущен
- Проверь `admin/index.html` - правильный ли URL (Render или localhost)

---

## 🎉 Результат:

✅ Постоянное хранилище данных (не исчезнут при деплое)
✅ Быстрее чем SQLite на продакшене
✅ Правильная архитектура
✅ Поддержка локальной разработки на SQLite
✅ Готово к масштабированию

