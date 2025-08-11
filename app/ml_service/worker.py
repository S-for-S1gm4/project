# app/ml_service/worker.py
"""
ML Worker для обработки задач предсказания участия в событиях
Подключается к RabbitMQ и обрабатывает ML задачи
"""
import json
import logging
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pika
import time
import os
import sys

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import get_settings
from services.user_service import UserService
from services.event_service import EventService
from models import User, Event

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MLWorker:
    """ML Worker для обработки задач предсказания"""

    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.settings = get_settings()
        self.connection = None
        self.channel = None

        # Инициализация ML модели (заглушка)
        self.model = self._init_ml_model()

        logger.info(f"ML Worker {self.worker_id} initialized")

    def _init_ml_model(self):
        """Инициализация ML модели (простая эвристическая модель)"""
        logger.info("Initializing ML model...")

        # В реальном проекте здесь была бы загрузка обученной модели
        # model = joblib.load('event_participation_model.pkl')

        # Пока используем простую эвристическую модель
        return {
            'version': '1.0',
            'features': [
                'user_balance', 'event_cost', 'balance_ratio',
                'user_activity_score', 'event_popularity',
                'time_to_event', 'user_interest_score'
            ],
            'initialized_at': datetime.utcnow()
        }

    def connect_to_rabbitmq(self) -> bool:
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

            # Объявляем очередь для ML задач
            self.channel.queue_declare(
                queue='ml_prediction_tasks',
                durable=True  # Очередь переживает перезапуск сервера
            )

            # Объявляем очередь для результатов
            self.channel.queue_declare(
                queue='ml_prediction_results',
                durable=True
            )

            # Настройка качества обслуживания (по одной задаче на воркер)
            self.channel.basic_qos(prefetch_count=1)

            logger.info(f"Worker {self.worker_id} connected to RabbitMQ")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False

    def validate_task_data(self, task_data: Dict[str, Any]) -> tuple[bool, str]:
        """Валидация данных задачи"""
        try:
            # Обязательные поля
            required_fields = ['task_id', 'user_id', 'event_id', 'user_features']
            for field in required_fields:
                if field not in task_data:
                    return False, f"Missing required field: {field}"

            # Валидация типов
            if not isinstance(task_data['user_id'], int):
                return False, "user_id must be integer"

            if not isinstance(task_data['event_id'], int):
                return False, "event_id must be integer"

            if not isinstance(task_data['user_features'], dict):
                return False, "user_features must be dict"

            # Проверка существования пользователя и события
            user = UserService.get_user_by_id(task_data['user_id'])
            if not user:
                return False, f"User {task_data['user_id']} not found"

            event = EventService.get_event_by_id(task_data['event_id'])
            if not event:
                return False, f"Event {task_data['event_id']} not found"

            logger.info(f"Task {task_data['task_id']} validation passed")
            return True, "Valid"

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation error: {str(e)}"

    def extract_features(self, user: User, event: Event, user_features: Dict) -> Dict[str, float]:
        """Извлечение признаков для ML модели"""
        try:
            # Базовые признаки
            features = {
                'user_balance': float(user.balance),
                'event_cost': float(event.cost),
                'balance_ratio': float(user.balance) / max(float(event.cost), 1.0),
                'current_participants': float(event.current_participants),
            }

            # Признаки активности пользователя
            user_transactions = UserService.get_user_transactions(user.id)
            features['transaction_count'] = len(user_transactions)
            features['avg_transaction_amount'] = sum(t.amount for t in user_transactions) / max(len(user_transactions), 1)

            # Признаки популярности события
            if event.max_participants:
                features['fill_rate'] = float(event.current_participants) / float(event.max_participants)
            else:
                features['fill_rate'] = 0.1  # Для событий без ограничений

            # Временные признаки
            if event.event_date:
                time_to_event = (event.event_date - datetime.utcnow()).days
                features['days_to_event'] = float(max(time_to_event, 0))
            else:
                features['days_to_event'] = 30.0  # Дефолтное значение

            # Пользовательские признаки
            features['interest_level'] = float(user_features.get('interest_level', 0.5))
            features['past_participation'] = float(user_features.get('past_participation', 0.3))
            features['event_type_preference'] = float(user_features.get('event_type_preference', 0.5))

            # Признаки роли пользователя
            features['is_admin'] = 1.0 if user.role == 'admin' else 0.0

            # Признаки возраста аккаунта
            account_age_days = (datetime.utcnow() - user.created_at).days
            features['account_age_days'] = float(account_age_days)
            features['account_age_weeks'] = float(account_age_days) / 7.0

            logger.info(f"Extracted {len(features)} features for user {user.id}, event {event.id}")
            return features

        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return {}

    def predict_participation(self, features: Dict[str, float]) -> Dict[str, Any]:
        """ML предсказание участия в событии"""
        try:
            logger.info("Running ML prediction...")

            # Эвристическая модель (в реальности здесь был бы вызов обученной модели)
            balance_ratio = features.get('balance_ratio', 0)
            interest_level = features.get('interest_level', 0.5)
            past_participation = features.get('past_participation', 0.3)
            fill_rate = features.get('fill_rate', 0)
            days_to_event = features.get('days_to_event', 30)
            transaction_count = features.get('transaction_count', 0)

            # Базовая оценка на основе баланса
            if balance_ratio < 0.5:
                base_score = 0.2
            elif balance_ratio < 1.0:
                base_score = 0.4
            elif balance_ratio < 2.0:
                base_score = 0.6
            else:
                base_score = 0.8

            # Корректировки на основе других факторов
            score = base_score

            # Интерес пользователя
            score += (interest_level - 0.5) * 0.3

            # Предыдущий опыт участия
            score += (past_participation - 0.3) * 0.2

            # Популярность события (умеренно заполненные события привлекательнее)
            if 0.3 <= fill_rate <= 0.7:
                score += 0.1
            elif fill_rate > 0.9:
                score -= 0.2  # Мало мест

            # Время до события
            if days_to_event < 3:
                score -= 0.1  # Слишком близко
            elif days_to_event > 60:
                score -= 0.1  # Слишком далеко

            # Активность пользователя
            if transaction_count > 5:
                score += 0.1

            # Ограничиваем score в диапазоне [0, 1]
            score = max(0.0, min(1.0, score))

            # Определяем категории
            if score >= 0.8:
                prediction = "very_likely_to_join"
                recommendation = "Отличный выбор! Настоятельно рекомендуем присоединиться."
            elif score >= 0.6:
                prediction = "likely_to_join"
                recommendation = "Хорошие шансы. Рекомендуем рассмотреть участие."
            elif score >= 0.4:
                prediction = "might_join"
                recommendation = "Стоит подумать. Оцените свой интерес и возможности."
            elif score >= 0.2:
                prediction = "unlikely_to_join"
                recommendation = "Возможно, стоит поискать что-то другое."
            else:
                prediction = "very_unlikely_to_join"
                recommendation = "Участие не рекомендуется."

            # Формируем детальный ответ
            result = {
                'prediction': prediction,
                'confidence': round(score, 3),
                'recommendation': recommendation,
                'feature_importance': {
                    'balance_ratio': round(balance_ratio, 2),
                    'interest_level': round(interest_level, 2),
                    'past_participation': round(past_participation, 2),
                    'event_popularity': round(fill_rate, 2)
                },
                'model_version': self.model['version'],
                'processed_at': datetime.utcnow().isoformat(),
                'worker_id': self.worker_id
            }

            logger.info(f"Prediction completed: {prediction} (confidence: {score:.3f})")
            return result

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                'error': f'Prediction failed: {str(e)}',
                'processed_at': datetime.utcnow().isoformat(),
                'worker_id': self.worker_id
            }

    def save_prediction_result(self, task_data: Dict, prediction_result: Dict) -> bool:
        """Сохранение результата предсказания"""
        try:
            # В реальном проекте здесь было бы сохранение в БД
            # Пока логируем и сохраняем в транзакцию пользователя

            user_id = task_data['user_id']
            event_id = task_data['event_id']

            description = (f"ML prediction: {prediction_result.get('prediction', 'unknown')} "
                          f"(confidence: {prediction_result.get('confidence', 0):.2f}) "
                          f"for event {event_id} by worker {self.worker_id}")

            # Записываем как транзакцию с нулевой суммой
            UserService.add_balance(user_id, 0.0, description)

            logger.info(f"Prediction result saved for user {user_id}, event {event_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save prediction result: {e}")
            return False

    def send_result_to_queue(self, result_data: Dict) -> bool:
        """Отправка результата в очередь результатов"""
        try:
            message = json.dumps(result_data, ensure_ascii=False)

            self.channel.basic_publish(
                exchange='',
                routing_key='ml_prediction_results',
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Делаем сообщение персистентным
                )
            )

            logger.info(f"Result sent to results queue: {result_data.get('task_id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to send result: {e}")
            return False

    def process_task(self, ch, method, properties, body):
        """Обработка ML задачи"""
        task_start_time = time.time()

        try:
            # Парсим задачу
            task_data = json.loads(body.decode('utf-8'))
            task_id = task_data.get('task_id', 'unknown')

            logger.info(f"Worker {self.worker_id} processing task {task_id}")

            # Валидация данных
            is_valid, validation_message = self.validate_task_data(task_data)

            if not is_valid:
                error_result = {
                    'task_id': task_id,
                    'status': 'failed',
                    'error': validation_message,
                    'worker_id': self.worker_id,
                    'processed_at': datetime.utcnow().isoformat(),
                    'processing_time_ms': int((time.time() - task_start_time) * 1000)
                }

                self.send_result_to_queue(error_result)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # Получаем данные пользователя и события
            user = UserService.get_user_by_id(task_data['user_id'])
            event = EventService.get_event_by_id(task_data['event_id'])

            # Извлекаем признаки
            features = self.extract_features(user, event, task_data['user_features'])

            if not features:
                error_result = {
                    'task_id': task_id,
                    'status': 'failed',
                    'error': 'Feature extraction failed',
                    'worker_id': self.worker_id,
                    'processed_at': datetime.utcnow().isoformat(),
                    'processing_time_ms': int((time.time() - task_start_time) * 1000)
                }

                self.send_result_to_queue(error_result)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # Выполняем предсказание
            prediction_result = self.predict_participation(features)

            # Формируем финальный результат
            final_result = {
                'task_id': task_id,
                'status': 'completed',
                'user_id': task_data['user_id'],
                'event_id': task_data['event_id'],
                'prediction': prediction_result,
                'features_used': list(features.keys()),
                'worker_id': self.worker_id,
                'processed_at': datetime.utcnow().isoformat(),
                'processing_time_ms': int((time.time() - task_start_time) * 1000)
            }

            # Сохраняем результат
            self.save_prediction_result(task_data, prediction_result)

            # Отправляем результат в очередь
            self.send_result_to_queue(final_result)

            # Подтверждаем обработку сообщения
            ch.basic_ack(delivery_tag=method.delivery_tag)

            logger.info(f"Task {task_id} completed successfully in {int((time.time() - task_start_time) * 1000)}ms")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse task JSON: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error(f"Task processing error: {e}")

            # Отправляем сообщение об ошибке
            error_result = {
                'task_id': task_data.get('task_id', 'unknown'),
                'status': 'error',
                'error': str(e),
                'worker_id': self.worker_id,
                'processed_at': datetime.utcnow().isoformat(),
                'processing_time_ms': int((time.time() - task_start_time) * 1000)
            }

            self.send_result_to_queue(error_result)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        """Запуск обработки задач"""
        try:
            logger.info(f"Worker {self.worker_id} starting to consume tasks...")

            self.channel.basic_consume(
                queue='ml_prediction_tasks',
                on_message_callback=self.process_task
            )

            logger.info(f"Worker {self.worker_id} waiting for messages. To exit press CTRL+C")
            self.channel.start_consuming()

        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id} stopped by user")
            self.channel.stop_consuming()

        except Exception as e:
            logger.error(f"Consuming error: {e}")

        finally:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info(f"Worker {self.worker_id} connection closed")

def main():
    """Главная функция для запуска воркера"""
    import argparse

    parser = argparse.ArgumentParser(description='ML Worker for Event Prediction')
    parser.add_argument('--worker-id', type=str, default='worker-1',
                       help='Unique worker identifier')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')

    args = parser.parse_args()

    # Настройка логирования
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    logger.info("="*50)
    logger.info(f"Starting ML Worker: {args.worker_id}")
    logger.info("="*50)

    # Создаем и запускаем воркер
    worker = MLWorker(args.worker_id)

    # Пытаемся подключиться к RabbitMQ с повторами
    max_retries = 10
    retry_delay = 5

    for attempt in range(max_retries):
        if worker.connect_to_rabbitmq():
            break

        logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
        time.sleep(retry_delay)
    else:
        logger.error("Failed to connect to RabbitMQ after all retries")
        return

    # Запускаем обработку
    worker.start_consuming()

if __name__ == "__main__":
    main()
