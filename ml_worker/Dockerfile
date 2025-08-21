FROM python:3.11-slim

# Создаем рабочую директорию
WORKDIR /ml_worker

# Копируем только необходимые файлы
COPY ./requirements.txt /ml_worker/

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /ml_worker/requirements.txt

# Копируем код
COPY . /ml_worker

# Запускаем воркер по умолчанию
CMD ["python", "worker.py"]
