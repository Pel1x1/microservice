# /tests/unit/test_part_model.py
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.part import Part, PartStatuses, PublishPartRequest


def make_part(**kwargs) -> Part:
    data = dict(id=uuid4(), store_id=uuid4(), name='Колодки тормозные', category='Тормоза',
                brand='Brembo', compatible_cars=['Toyota Camry 2018'],
                created_at=datetime.now(timezone.utc))
    return Part(**{**data, **kwargs})


def test_part_creation() -> None:
    part = make_part()
    assert part.status == PartStatuses.PUBLISHED
    assert part.compatible_cars == ['Toyota Camry 2018']


def test_part_cars_required() -> None:
    with pytest.raises(ValidationError):
        make_part(compatible_cars=[])


def test_part_name_required() -> None:
    with pytest.raises(ValidationError):
        make_part(name='')


def test_part_category_required() -> None:
    with pytest.raises(ValidationError):
        make_part(category='')


def test_part_assignment_is_validated() -> None:
    part = make_part()
    with pytest.raises(ValidationError):
        part.status = 'archived'


def test_publish_request_parses_json() -> None:
    store_id = uuid4()
    request = PublishPartRequest.model_validate({
        'store_id': str(store_id), 'name': 'Фильтр', 'category': 'Фильтры', 'brand': 'Mann',
        'compatible_cars': ['Kia Rio 2020', 'Hyundai Solaris 2020']})
    assert request.store_id == store_id
    assert len(request.compatible_cars) == 2
