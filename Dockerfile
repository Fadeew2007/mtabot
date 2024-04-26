# Виберіть базовий образ
FROM python-3.12.3

# Встановіть робочу директорію у контейнері
WORKDIR /app

# Копіюйте файли залежностей
COPY requirements.txt .

# Встановіть залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюйте всі файли проекту в контейнер
COPY . .

# Вкажіть команду для запуску вашого бота
CMD ["python", "price-availability.py"]
