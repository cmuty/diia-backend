@echo off
cd /d "C:\Users\nutip\OneDrive\Desktop\проекты\DiiaBackend"
echo Проверка статуса...
git status
echo.
echo Добавление всех файлов...
git add .
echo.
echo Коммит изменений...
git commit -m "Исправлены все конфликты мерджа - чистая версия"
echo.
echo Отправка на GitHub...
git push origin main
echo.
echo Готово!
pause

