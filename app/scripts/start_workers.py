#!/usr/bin/env python3
# app/scripts/start_workers.py
"""
Скрипт для запуска нескольких ML воркеров
"""
import os
import sys
import subprocess
import signal
import time
import logging
from typing import List, Dict
import argparse

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import get_settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MLWorkersManager:
    """Менеджер для управления несколькими ML воркерами"""

    def __init__(self, num_workers: int = 3, log_level: str = "INFO"):
        self.num_workers = num_workers
        self.log_level = log_level
        self.workers: Dict[str, subprocess.Popen] = {}
        self.settings = get_settings()

        # Обработчик сигналов для корректного завершения
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logger.info(f"Received signal {signum}, shutting down workers...")
        self.stop_all_workers()
        sys.exit(0)

    def start_worker(self, worker_id: str) -> bool:
        """Запуск одного воркера"""
        try:
            # Путь к скрипту воркера
            worker_script = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "ml_service",
                "worker.py"
            )

            # Команда для запуска воркера
            cmd = [
                sys.executable,
                worker_script,
                f"--worker-id={worker_id}",
                f"--log-level={self.log_level}"
            ]

            # Создаем лог файл для воркера
            log_dir = "logs/ml_workers"
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{worker_id}.log")

            # Запускаем процесс
            with open(log_file, "a") as log_f:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    cwd=os.path.dirname(os.path.dirname(__file__))
                )

            self.workers[worker_id] = process
            logger.info(f"Started worker {worker_id} (PID: {process.pid})")
            return True

        except Exception as e:
            logger.error(f"Failed to start worker {worker_id}: {e}")
            return False

    def stop_worker(self, worker_id: str) -> bool:
        """Остановка одного воркера"""
        try:
            if worker_id in self.workers:
                process = self.workers[worker_id]
                if process.poll() is None:  # Процесс еще работает
                    process.terminate()

                    # Ждем завершения процесса
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        # Принудительное завершение
                        process.kill()
                        process.wait()

                    logger.info(f"Stopped worker {worker_id}")

                del self.workers[worker_id]
                return True
            else:
                logger.warning(f"Worker {worker_id} not found")
                return False

        except Exception as e:
            logger.error(f"Failed to stop worker {worker_id}: {e}")
            return False

    def start_all_workers(self) -> bool:
        """Запуск всех воркеров"""
        logger.info(f"Starting {self.num_workers} ML workers...")

        success_count = 0
        for i in range(1, self.num_workers + 1):
            worker_id = f"worker-{i}"
            if self.start_worker(worker_id):
                success_count += 1
                time.sleep(1)  # Небольшая задержка между запусками

        logger.info(f"Successfully started {success_count}/{self.num_workers} workers")
        return success_count == self.num_workers

    def stop_all_workers(self) -> bool:
        """Остановка всех воркеров"""
        logger.info("Stopping all ML workers...")

        worker_ids = list(self.workers.keys())
        success_count = 0

        for worker_id in worker_ids:
            if self.stop_worker(worker_id):
                success_count += 1

        logger.info(f"Successfully stopped {success_count}/{len(worker_ids)} workers")
        return success_count == len(worker_ids)

    def get_worker_status(self) -> Dict[str, str]:
        """Получение статуса всех воркеров"""
        status = {}
        for worker_id, process in self.workers.items():
            if process.poll() is None:
                status[worker_id] = "running"
            else:
                status[worker_id] = f"stopped (exit code: {process.returncode})"

        return status

    def restart_worker(self, worker_id: str) -> bool:
        """Перезапуск одного воркера"""
        logger.info(f"Restarting worker {worker_id}...")
        self.stop_worker(worker_id)
        time.sleep(2)
        return self.start_worker(worker_id)

    def monitor_workers(self, check_interval: int = 30) -> None:
        """Мониторинг воркеров и автоперезапуск при необходимости"""
        logger.info(f"Starting worker monitoring (check interval: {check_interval}s)")

        try:
            while True:
                dead_workers = []

                for worker_id, process in self.workers.items():
                    if process.poll() is not None:
                        logger.warning(f"Worker {worker_id} died (exit code: {process.returncode})")
                        dead_workers.append(worker_id)

                # Перезапускаем мертвые воркеры
                for worker_id in dead_workers:
                    logger.info(f"Restarting dead worker {worker_id}")
                    self.restart_worker(worker_id)

                time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user")

    def show_status(self) -> None:
        """Показать статус всех воркеров"""
        status = self.get_worker_status()

        print("\n" + "="*50)
        print("ML WORKERS STATUS")
        print("="*50)

        for worker_id, worker_status in status.items():
            status_color = "🟢" if worker_status == "running" else "🔴"
            print(f"{status_color} {worker_id}: {worker_status}")

        print(f"\nTotal workers: {len(status)}")
        running_count = sum(1 for s in status.values() if s == "running")
        print(f"Running: {running_count}/{len(status)}")
        print("="*50 + "\n")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='ML Workers Manager')
    parser.add_argument('--workers', type=int, default=3,
                       help='Number of workers to start (default: 3)')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--monitor', action='store_true',
                       help='Enable automatic worker monitoring and restart')
    parser.add_argument('--check-interval', type=int, default=30,
                       help='Monitoring check interval in seconds (default: 30)')
    parser.add_argument('--action', type=str,
                       choices=['start', 'stop', 'restart', 'status'],
                       default='start',
                       help='Action to perform (default: start)')

    args = parser.parse_args()

    # Создаем менеджер воркеров
    manager = MLWorkersManager(
        num_workers=args.workers,
        log_level=args.log_level
    )

    try:
        if args.action == 'start':
            logger.info("="*60)
            logger.info("Starting ML Workers Manager")
            logger.info("="*60)

            # Проверяем доступность RabbitMQ
            try:
                from ml_service.publisher import MLTaskPublisher
                publisher = MLTaskPublisher()
                if not publisher.connect():
                    logger.error("Cannot connect to RabbitMQ! Make sure it's running.")
                    return False
                publisher.close()
                logger.info("✅ RabbitMQ connection test passed")
            except Exception as e:
                logger.error(f"RabbitMQ connection error: {e}")
                return False

            # Запускаем воркеры
            if manager.start_all_workers():
                logger.info("✅ All workers started successfully!")

                if args.monitor:
                    logger.info("Starting monitoring mode...")
                    manager.monitor_workers(args.check_interval)
                else:
                    logger.info("Workers started. Use Ctrl+C to stop.")
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        logger.info("Shutting down...")
            else:
                logger.error("❌ Failed to start all workers")
                return False

        elif args.action == 'stop':
            logger.info("Stopping all workers...")
            manager.stop_all_workers()

        elif args.action == 'restart':
            logger.info("Restarting all workers...")
            manager.stop_all_workers()
            time.sleep(2)
            manager.start_all_workers()

        elif args.action == 'status':
            manager.show_status()

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
