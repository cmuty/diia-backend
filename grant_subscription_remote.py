"""
Выдать подписку пользователю на Render через API
"""
import requests
from datetime import datetime, timedelta

# URL твоего Render сервера
RENDER_URL = "https://diia-backend.onrender.com"

def grant_subscription():
    login = input("Введи логин пользователя: ").strip()
    
    # Сначала получим данные пользователя
    response = requests.get(f"{RENDER_URL}/api/user/{login}")
    
    if response.status_code != 200:
        print(f"❌ Пользователь '{login}' не найден на Render")
        return
    
    user_data = response.json()
    print(f"\n👤 Найден: {user_data['full_name']}")
    print(f"📊 Текущая подписка: {'✅ Активна' if user_data['subscription_active'] else '❌ Нет'}")
    
    print("\n💎 Выбери тип подписки:")
    print("1. Basic")
    print("2. Premium")
    print("3. Lifetime (назавжди)")
    
    choice = input("Выбор: ").strip()
    
    sub_types = {
        "1": "basic",
        "2": "premium",
        "3": "lifetime"
    }
    
    sub_type = sub_types.get(choice)
    if not sub_type:
        print("❌ Неверный выбор")
        return
    
    days = input("На сколько дней? (Enter для бессрочной): ").strip()
    
    until = None
    if days and days.isdigit():
        until_date = datetime.now() + timedelta(days=int(days))
        until = until_date.isoformat()
    
    # ВАЖНО: Нужно создать API эндпоинт на Render для обновления подписки
    # Пока что можно только вручную через SQL или через бота
    
    print("\n⚠️ ВНИМАНИЕ!")
    print("Для выдачи подписки на Render нужно:")
    print("1. Либо использовать Telegram бота (команды админа)")
    print("2. Либо добавить API эндпоинт /api/admin/grant-subscription")
    print("3. Либо подключиться к БД Render напрямую")
    print("\nТекущий скрипт работает только для локальной БД!")

if __name__ == "__main__":
    grant_subscription()

