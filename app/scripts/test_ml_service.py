#!/usr/bin/env python3
# app/scripts/test_ml_service.py
"""
Скрипт для тестирования ML сервиса и RabbitMQ интеграции
"""
import sys
import os
import time
import json
import asyncio
from typing import Dict, List
import logging

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import get_settings
from database.database import test_connection, init_db
from services.user_service import UserService
from services.event_service import EventService
from ml_service.publisher import MLTaskPublisher

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MLServiceTester:
    """Тестировщик ML сервиса"""

    def __init__(self):
        self.settings = get_settings()
        self.publisher = MLTaskPublisher()
        self.test_results: List[Dict] = []

    def setup_test_data(self) -> bool:
        """Создание тестовых данных"""
        try:
            logger.info("Setting up test data...")

            # Проверяем подключение к БД
            if not test_connection():
                logger.error("Database connection failed!")
                return False

            # Создаем тестового пользователя
            try:
                test_user = UserService.create_user(
                    email="mltest@example.com",
                    username="mltest",
                    password="test123",
                    full_name="ML Test User"
                )

                # Добавляем баланс
                UserService.add_balance(test_user.id, 1000.0, "Test balance")

                logger.info(f"Created test user: {test_user.id}")
                self.test_user_id = test_user.id

            except ValueError:
                # Пользователь уже существует
                test_user = UserService.get_user_by_email("mltest@example.com")
                self.test_user_id = test_user.id
                logger.info(f"Using existing test user: {test_user.id}")

            # Создаем тестовое событие
            try:
                test_event = EventService.create_event(
                    title="ML Test Event",
                    description="Event for ML testing",
                    creator_id=self.test_user_id,
                    cost=100.0,
                    max_participants=20
                )

                # Активируем событие
                EventService.activate_event(test_event.id)

                logger.info(f"Created test event: {test_event.id}")
                self.test_event_id = test_event.id

            except Exception as e:
                # Используем существующее событие
                events = EventService.get_active_events()
                if events:
                    self.test_event_id = events[0].id
                    logger.info(f"Using existing test event: {self.test_event_id}")
                else:
                    logger.error("No events available for testing")
                    return False

            return True

        except Exception as e:
            logger.error(f"Test data setup failed: {e}")
            return False

    def test_rabbitmq_connection(self) -> bool:
        """Тест подключения к RabbitMQ"""
        logger.info("Testing RabbitMQ connection...")

        try:
            if self.publisher.connect():
                logger.info("✅ RabbitMQ connection successful")
                return True
            else:
                logger.error("❌ RabbitMQ connection failed")
                return False

        except Exception as e:
            logger.error(f"❌ RabbitMQ connection error: {e}")
            return False

    def test_single_prediction(self) -> bool:
        """Тест одного ML предсказания"""
        logger.info("Testing single ML prediction...")

        try:
            # Подготавливаем данные для предсказания
            user_features = {
                "interest_level": 0.8,
                "past_participation": 0.6,
                "event_type_preference": 0.7,
                "time_flexibility": 0.9
            }

            # Отправляем задачу
            task_id = self.publisher.publish_prediction_task(
                user_id=self.test_user_id,
                event_id=self.test_event_id,
                user_features=user_features
            )

            if not task_id:
                logger.error("❌ Failed to publish prediction task")
                return False

            logger.info(f"📤 Published prediction task: {task_id}")

            # Ждем результат
            max_wait_time = 30  # 30 секунд
            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                result = self.publisher.get_result()

                if result and result.get('task_id') == task_id:
                    logger.info(f"📥 Received result for task: {task_id}")

                    # Анализируем результат
                    if result.get('status') == 'completed':
                        prediction = result.get('prediction', {})
                        logger.info(f"✅ Prediction: {prediction.get('prediction')}")
                        logger.info(f"✅ Confidence: {prediction.get('confidence')}")
                        logger.info(f"✅ Worker: {result.get('worker_id')}")
                        logger.info(f"✅ Processing time: {result.get('processing_time_ms')}ms")

                        self.test_results.append({
                            'test_type': 'single_prediction',
                            'status': 'success',
                            'task_id': task_id,
                            'result': result,
                            'processing_time_ms': result.get('processing_time_ms')
                        })

                        return True

                    else:
                        logger.error(f"❌ Prediction failed: {result.get('error')}")
                        self.test_results.append({
                            'test_type': 'single_prediction',
                            'status': 'failed',
                            'task_id': task_id,
                            'error': result.get('error')
                        })
                        return False

                time.sleep(1)

            logger.error(f"❌ Timeout waiting for result (task: {task_id})")
            self.test_results.append({
                'test_type': 'single_prediction',
                'status': 'timeout',
                'task_id': task_id
            })
            return False

        except Exception as e:
            logger.error(f"❌ Single prediction test failed: {e}")
            return False

    def test_multiple_predictions(self, count: int = 5) -> bool:
        """Тест множественных ML предсказаний"""
        logger.info(f"Testing {count} concurrent ML predictions...")

        try:
            sent_tasks = []

            # Отправляем несколько задач
            for i in range(count):
                user_features = {
                    "interest_level": 0.5 + (i * 0.1),
                    "past_participation": 0.3 + (i * 0.1),
                    "event_type_preference": 0.6 + (i * 0.05),
                    "test_iteration": i
                }

                task_id = self.publisher.publish_prediction_task(
                    user_id=self.test_user_id,
                    event_id=self.test_event_id,
                    user_features=user_features
                )

                if task_id:
                    sent_tasks.append(task_id)
                    logger.info(f"📤 Sent task {i+1}/{count}: {task_id}")
                    time.sleep(0.5)  # Небольшая задержка между отправками

            if not sent_tasks:
                logger.error("❌ Failed to send any tasks")
                return False

            logger.info(f"📤 Sent {len(sent_tasks)} tasks, waiting for results...")

            # Собираем результаты
            received_results = []
            max_wait_time = 60  # 60 секунд для всех задач
            start_time = time.time()

            while len(received_results) < len(sent_tasks) and time.time() - start_time < max_wait_time:
                result = self.publisher.get_result()

                if result and result.get('task_id') in sent_tasks:
                    received_results.append(result)
                    logger.info(f"📥 Received result {len(received_results)}/{len(sent_tasks)}: {result.get('task_id')}")

                time.sleep(1)

            # Анализируем результаты
            successful_results = [r for r in received_results if r.get('status') == 'completed']

            logger.info(f"✅ Received {len(received_results)}/{len(sent_tasks)} results")
            logger.info(f"✅ Successful: {len(successful_results)}")

            if successful_results:
                processing_times = [r.get('processing_time_ms', 0) for r in successful_results]
                avg_time = sum(processing_times) / len(processing_times)
                logger.info(f"✅ Average processing time: {avg_time:.1f}ms")

                # Проверяем распределение по воркерам
                workers = [r.get('worker_id') for r in successful_results]
                unique_workers = set(workers)
                logger.info(f"✅ Used workers: {unique_workers}")

            self.test_results.append({
                'test_type': 'multiple_predictions',
                'sent_count': len(sent_tasks),
                'received_count': len(received_results),
                'successful_count': len(successful_results),
                'average_processing_time_ms': avg_time if successful_results else 0,
                'used_workers': list(unique_workers) if successful_results else []
            })

            return len(successful_results) >= len(sent_tasks) * 0.8  # 80% успешных результатов

        except Exception as e:
            logger.error(f"❌ Multiple predictions test failed: {e}")
            return False

    def test_invalid_data(self) -> bool:
        """Тест обработки некорректных данных"""
        logger.info("Testing invalid data handling...")

        try:
            # Тест с несуществующим пользователем
            task_id = self.publisher.publish_prediction_task(
                user_id=99999,  # Несуществующий ID
                event_id=self.test_event_id,
                user_features={"test": "invalid_user"}
            )

            if task_id:
                # Ждем результат
                for _ in range(10):
                    result = self.publisher.get_result()
                    if result and result.get('task_id') == task_id:
                        if result.get('status') == 'failed':
                            logger.info("✅ Invalid user ID correctly rejected")
                            return True
                        break
                    time.sleep(1)

            return False

        except Exception as e:
            logger.error(f"❌ Invalid data test failed: {e}")
            return False

    def test_performance(self, load_count: int = 20) -> bool:
        """Тест производительности"""
        logger.info(f"Testing performance with {load_count} concurrent tasks...")

        try:
            start_time = time.time()

            # Отправляем много задач одновременно
            sent_tasks = []
            for i in range(load_count):
                task_id = self.publisher.publish_prediction_task(
                    user_id=self.test_user_id,
                    event_id=self.test_event_id,
                    user_features={
                        "interest_level": 0.5,
                        "performance_test": True,
                        "batch_id": i
                    }
                )
                if task_id:
                    sent_tasks.append(task_id)

            send_time = time.time() - start_time
            logger.info(f"📤 Sent {len(sent_tasks)} tasks in {send_time:.2f}s")

            # Собираем результаты
            received_results = []
            max_wait_time = 120  # 2 минуты
            start_wait = time.time()

            while len(received_results) < len(sent_tasks) and time.time() - start_wait < max_wait_time:
                result = self.publisher.get_result()
                if result and result.get('task_id') in sent_tasks:
                    received_results.append(result)
                time.sleep(0.1)

            total_time = time.time() - start_time
            successful_results = [r for r in received_results if r.get('status') == 'completed']

            # Статистика производительности
            if successful_results:
                processing_times = [r.get('processing_time_ms', 0) for r in successful_results]
                avg_processing_time = sum(processing_times) / len(processing_times)
                throughput = len(successful_results) / total_time

                logger.info(f"✅ Performance test results:")
                logger.info(f"   - Total time: {total_time:.2f}s")
                logger.info(f"   - Successful: {len(successful_results)}/{len(sent_tasks)}")
                logger.info(f"   - Throughput: {throughput:.2f} predictions/sec")
                logger.info(f"   - Avg processing time: {avg_processing_time:.1f}ms")

                self.test_results.append({
                    'test_type': 'performance',
                    'load_count': load_count,
                    'total_time_s': total_time,
                    'successful_count': len(successful_results),
                    'throughput_per_sec': throughput,
                    'avg_processing_time_ms': avg_processing_time
                })

                return True

            return False

        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return False

    def generate_report(self) -> None:
        """Генерация отчета о тестировании"""
        logger.info("="*60)
        logger.info("ML SERVICE TEST REPORT")
        logger.info("="*60)

        for result in self.test_results:
            test_type = result.get('test_type', 'unknown')
            logger.info(f"\n📊 {test_type.upper().replace('_', ' ')}:")

            if test_type == 'single_prediction':
                status = result.get('status', 'unknown')
                logger.info(f"   Status: {'✅' if status == 'success' else '❌'} {status}")
                if status == 'success':
                    logger.info(f"   Processing time: {result.get('processing_time_ms')}ms")

            elif test_type == 'multiple_predictions':
                success_rate = (result.get('successful_count', 0) / result.get('sent_count', 1)) * 100
                logger.info(f"   Sent: {result.get('sent_count')}")
                logger.info(f"   Received: {result.get('received_count')}")
                logger.info(f"   Success rate: {success_rate:.1f}%")
                logger.info(f"   Avg processing time: {result.get('average_processing_time_ms'):.1f}ms")
                logger.info(f"   Workers used: {len(result.get('used_workers', []))}")

            elif test_type == 'performance':
                logger.info(f"   Load: {result.get('load_count')} concurrent tasks")
                logger.info(f"   Total time: {result.get('total_time_s'):.2f}s")
                logger.info(f"   Throughput: {result.get('throughput_per_sec'):.2f} predictions/sec")
                logger.info(f"   Avg processing: {result.get('avg_processing_time_ms'):.1f}ms")

        logger.info("\n" + "="*60)

    def run_all_tests(self) -> bool:
        """Запуск всех тестов"""
        logger.info("🚀 Starting ML Service comprehensive testing...")

        # 1. Настройка тестовых данных
        if not self.setup_test_data():
            logger.error("❌ Test data setup failed")
            return False

        # 2. Тест подключения к RabbitMQ
        if not self.test_rabbitmq_connection():
            logger.error("❌ RabbitMQ connection test failed")
            return False

        # 3. Тест одного предсказания
        if not self.test_single_prediction():
            logger.error("❌ Single prediction test failed")
            return False

        # 4. Тест множественных предсказаний
        if not self.test_multiple_predictions(5):
            logger.error("❌ Multiple predictions test failed")
            return False

        # 5. Тест некорректных данных
        if not self.test_invalid_data():
            logger.error("❌ Invalid data test failed")
            return False

        # 6. Тест производительности
        if not self.test_performance(10):
            logger.error("❌ Performance test failed")
            return False

        # 7. Генерация отчета
        self.generate_report()

        logger.info("✅ All tests completed successfully!")
        return True


def main():
    """Главная функция"""
    tester = MLServiceTester()

    try:
        success = tester.run_all_tests()
        return success

    except KeyboardInterrupt:
        logger.info("Testing interrupted by user")
        return False

    except Exception as e:
        logger.error(f"Testing failed with error: {e}")
        return False

    finally:
        # Закрываем соединения
        if hasattr(tester, 'publisher'):
            tester.publisher.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
