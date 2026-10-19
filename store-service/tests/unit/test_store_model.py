# /tests/unit/test_store_model.py
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.store import Store, StoreStatuses, CreateStoreRequest


def test_store_creation() -> None:
    store_id, owner_id = uuid4(), uuid4()
    created_at = datetime.now(timezone.utc)
    store = Store(id=store_id, owner_id=owner_id, name='АвтоМир', created_at=created_at)
    assert dict(store) == {'id': store_id, 'owner_id': owner_id, 'name': 'АвтоМир',
                           'status': StoreStatuses.PENDING, 'created_at': created_at}


def test_store_name_required() -> None:
    with pytest.raises(ValidationError):
        Store(id=uuid4(), owner_id=uuid4(), name='', created_at=datetime.now(timezone.utc))


def test_store_owner_required() -> None:
    with pytest.raises(ValidationError):
        Store(id=uuid4(), name='a', created_at=datetime.now(timezone.utc))


def test_store_assignment_is_validated() -> None:
    store = Store(id=uuid4(), owner_id=uuid4(), name='a', created_at=datetime.now(timezone.utc))
    with pytest.raises(ValidationError):
        store.status = 'unknown'


def test_create_request_parses_json() -> None:
    owner_id = uuid4()
    request = CreateStoreRequest.model_validate({'owner_id': str(owner_id), 'name': 'АвтоМир'})
    assert request.owner_id == owner_id
