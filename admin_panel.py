"""
Админ панель для управления пользователями и подписками
"""
import asyncio
from database.models import Database
from datetime import datetime, timedelta


async def main():
    db = Database("database/diia.db")
    await db.init_db()
    
    print("=" * 60)
    print("  DIIA - АДМИН ПАНЕЛЬ")
    print("=" * 60)
    
    while True:
        print("\n📋 Меню:")
        print("1. Показать всех пользователей")
        print("2. Выдать подписку пользователю")
        print("3. Забрать подписку")
        print("4. Поиск пользователя по логину")
        print("0. Выход")
        
        choice = input("\nВыберите действие: ").strip()
        
        if choice == "1":
            await show_all_users(db)
        elif choice == "2":
            await grant_subscription(db)
        elif choice == "3":
            await remove_subscription(db)
        elif choice == "4":
            await search_user(db)
        elif choice == "0":
            print("\n👋 До встречи!")
            break
        else:
            print("❌ Неверный выбор")


async def show_all_users(db):
    """Показать всех пользователей"""
    users = await db.get_all_users()
    
    if not users:
        print("\n❌ Пользователей нет")
        return
    
    print("\n" + "=" * 100)
    print(f"{'ID':<5} {'Логин':<15} {'ФИО':<30} {'Подписка':<15} {'Тип':<12}")
    print("=" * 100)
    
    for user in users:
        sub_status = "✅ Активна" if user['subscription_active'] else "❌ Нет"
        print(f"{user['id']:<5} {user['login']:<15} {user['full_name']:<30} {sub_status:<15} {user['subscription_type']:<12}")
    
    print("=" * 100)


async def grant_subscription(db):
    """Выдать подписку"""
    login = input("\n🔑 Введите логин пользователя: ").strip()
    
    user = await db.get_user_by_login(login)
    if not user:
        print(f"❌ Пользователь '{login}' не найден")
        return
    
    print(f"\n👤 Найден: {user['full_name']}")
    print(f"📊 Текущая подписка: {'✅ Активна' if user['subscription_active'] else '❌ Нет'}")
    print(f"🎫 Тип: {user['subscription_type']}")
    
    print("\n💎 Выберите тип подписки:")
    print("1. Basic (базовая)")
    print("2. Premium (премиум)")
    print("3. Безкоштовна")
    
    sub_choice = input("Выбор: ").strip()
    
    sub_types = {
        "1": "basic",
        "2": "premium",
        "3": "безкоштовна"
    }
    
    sub_type = sub_types.get(sub_choice)
    if not sub_type:
        print("❌ Неверный выбор")
        return
    
    print("\n📅 На сколько дней выдать подписку?")
    days = input("Дней (или Enter для бессрочной): ").strip()
    
    until = None
    if days and days.isdigit():
        until_date = datetime.now() + timedelta(days=int(days))
        until = until_date.isoformat()
    
    await db.update_subscription(user['id'], True, sub_type, until)
    
    print(f"\n✅ Подписка выдана!")
    print(f"👤 Пользователь: {user['full_name']}")
    print(f"🎫 Тип: {sub_type}")
    print(f"📅 До: {until if until else 'Бессрочно'}")


async def remove_subscription(db):
    """Забрать подписку"""
    login = input("\n🔑 Введите логин пользователя: ").strip()
    
    user = await db.get_user_by_login(login)
    if not user:
        print(f"❌ Пользователь '{login}' не найден")
        return
    
    print(f"\n👤 Найден: {user['full_name']}")
    print(f"📊 Текущая подписка: {'✅ Активна' if user['subscription_active'] else '❌ Нет'}")
    
    confirm = input("\n⚠️  Вы уверены? (да/нет): ").strip().lower()
    
    if confirm == "да" or confirm == "yes":
        await db.update_subscription(user['id'], False, "безкоштовна", None)
        print(f"\n✅ Подписка отменена для {user['full_name']}")
    else:
        print("❌ Отменено")


async def search_user(db):
    """Поиск пользователя"""
    login = input("\n🔍 Введите логин: ").strip()
    
    user = await db.get_user_by_login(login)
    if not user:
        print(f"❌ Пользователь '{login}' не найден")
        return
    
    last_login = user['last_login'] if user['last_login'] else "Никогда"
    if last_login != "Никогда":
        try:
            dt = datetime.fromisoformat(last_login)
            last_login = dt.strftime("%d.%m.%Y в %H:%M")
        except:
            pass
    
    print("\n" + "=" * 60)
    print(f"👤 ФИО: {user['full_name']}")
    print(f"🗓️  Дата рождения: {user['birth_date']}")
    print(f"🔑 Логин: {user['login']}")
    print(f"📲 Telegram ID: {user['telegram_id']}")
    print(f"📊 Подписка: {'✅ Активна' if user['subscription_active'] else '❌ Неактивна'}")
    print(f"🎫 Тип подписки: {user['subscription_type']}")
    print(f"📅 Действует до: {user['subscription_until'] if user['subscription_until'] else 'Бессрочно'}")
    print(f"🕐 Последний вход: {last_login}")
    print(f"📝 Зарегистрирован: {user['registered_at']}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Выход...")

