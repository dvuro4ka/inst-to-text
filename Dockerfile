# Базовый образ с Python 3.11.4
FROM python:3.11.4-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt requirements.txt
RUN  python3 -m pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Открываем порт 5000 для Flask
EXPOSE 5000

# Команда для запуска Flask-приложения
CMD ["python", "app.py"]
