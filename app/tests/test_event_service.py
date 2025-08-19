"""
Тесты для EventService - сервиса работы с событиями
"""
import pytest
from datetime import datetime, timedelta
from services.event_service import EventService
from services.user_service import UserService
from models import EventStatus, TransactionType


class TestEventCreation:
    """Тесты создания событий"""

    def test_create_event_success(self, created_user, sample_event_data):
        """Тест успешного создания события"""
        event = EventService.create_event(
            creator_id=created_user.id,
            **sample_event_data
        )

        assert event.id is not None
        assert event.title == sample_event_data["title"]
        assert event.description == sample_event_data["description"]
        assert event.cost == sample_event_data["cost"]
        assert event.max_participants == sample_event_data["max_participants"]
        assert event.event_date == sample_event_data["event_date"]
        assert event.creator_id == created_user.id
        assert event.status == EventStatus.DRAFT
        assert event.current_participants == 0
        assert event.created_at is not None

    def test_create_event_minimal_data(self, created_user):
        """Тест создания события с минимальными данными"""
        minimal_data = {
            "title": "Minimal Event",
            "description": "Simple test event",
            "creator_id": created_user.id
        }

        event = EventService.create_event(**minimal_data)

        assert event.id is not None
        assert event.title == minimal_data["title"]
        assert event.cost == 0.0
        assert event.max_participants is None
        assert event.event_date is None
        assert event.status == EventStatus.DRAFT

    def test_create_free_event(self, created_user):
        """Тест создания бесплатного события"""
        event_data = {
            "title": "Free Workshop",
            "description": "A free community workshop",
            "creator_id": created_user.id,
            "cost": 0.0,
            "max_participants": 100
        }

        event = EventService.create_event(**event_data)
