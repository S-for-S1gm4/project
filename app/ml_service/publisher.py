# app/ml_service/publisher.py
"""
ML Task Publisher - отправляет задачи предсказания в RabbitMQ
"""
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import pika

from database.config import get_settings

logger = logging.getLogger(__name__)

class MLTaskPublisher:
    """Издатель ML задач в RabbitMQ"""

    def __init__(self):
        self.settings = get_settings()
        self.connection = None
        self.channel = None

    def connect(self) -> bool:
        """Подключение к RabbitMQ"""
        try:
            connection_params = pika.ConnectionParameters(
                host=self.settings.RABBITMQ_HOST,
                port=self.settings.RABBITMQ_PORT,
                credentials=pika.PlainCredentials(
                    self.settings.RABBITMQ_USER,
                    self.settings.RABBITMQ_PASSWORD
                )
            )

            self.connection = pika.BlockingConnection(connection_params)
            self.channel = self.connection.channel()

            # Объявляем очереди
            self.channel.queue_declare(queue='ml_prediction_tasks', durable=True)
            self.channel.queue_declare(queue='ml_prediction_results', durable=True)

            logger.info("ML Publisher connected to RabbitMQ")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False

    def publish_prediction_task(self, user_id: int, event_id: int,
                              user_features: Dict[str, Any]) -> Optional[str]:
        """
        Публикация задачи ML предсказания

        Args:
            user_id: ID пользователя
            event_id: ID события
            user_features: Дополнительные характеристики пользователя

        Returns:
            task_id если успешно, None если ошибка
        """
        try:
            if not self.connection or self.connection.is_closed:
                if not self.connect():
                    return None

            # Генерируем уникальный ID задачи
            task_id = str(uuid.uuid4())

            # Формируем задачу
            task_data = {
                'task_id': task_id,
                'user_id': user_id,
                'event_id': event_id,
                'user_features': user_features,
                'created_at': datetime.utcnow().isoformat(),
                'priority': user_features.get('priority', 'normal')
            }

            # Сериализуем в JSON
            message = json.dumps(task_data, ensure_ascii=False)

            # Отправляем в очередь
            self.channel.basic_publish(
                exchange='',
                routing_key='ml_prediction_tasks',
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Персистентное сообщение
                    message_id=task_id,
                    timestamp=int(datetime.utcnow().timestamp())
                )
            )

            logger.info(f"Published ML task {task_id} for user {user_id}, event {event_id}")
            return task_id

        except Exception as e:
            logger.error(f"Failed to publish ML task: {e}")
            return None

    def get_result(self, timeout: int = 30) -> Optional[Dict]:
        """
        Получение результата из очереди результатов

        Args:
            timeout: Таймаут ожидания в секундах

        Returns:
            Результат или None
        """
        try:
            if not self.connection or self.connection.is_closed:
                if not self.connect():
                    return None

            method_frame, header_frame, body = self.channel.basic_get(
                queue='ml_prediction_results',
                auto_ack=True
            )

            if method_frame:
                result_data = json.loads(body.decode('utf-8'))
                logger.info(f"Received result: {result_data.get('task_id')}")
                return result_data

            return None

        except Exception as e:
            logger.error(f"Failed to get result: {e}")
            return None

    def close(self):
        """Закрытие соединения"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("ML Publisher connection closed")

# Глобальный экземпляр для использования в API
ml_publisher = MLTaskPublisher()
