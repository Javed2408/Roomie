"""Tests for the society directory: public reading, admin management,
duplicate prevention, history, importing candidates and retiring samples."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DirectoryEvent, Locality, Society, UserSocietyPreference
from app.models.enums import DirectoryStatus
from app.scripts.directory import DEFAULT_FILE
from app.services import directory as directory_service
from tests import factories
from tests.helpers import log_in, make_admin_account, sign_up

pytestmark = pytest.mark.integration

ADMIN = "/api/v1/admin/directory"


@pytest.fixture
def admin(new_client: Callable[[], TestClient], db: Session) -> tuple[TestClient, dict[str, str]]:
    """A browser signed in as an administrator, and its change headers."""
    make_admin_account(db)
    client = new_client()
    return client, log_in(client, "admin@example.com")


# --- Public reading ------------------------------------------------------


def test_only_verified_active_records_are_public(api: TestClient, db: Session) -> None:
    town = factories.make_locality(db, "Public Town")
    factories.make_society(db, "Shown Residency", locality=town)
    factories.make_society(db, "Unchecked Residency", locality=town, verified=False)
    factories.make_society(db, "Switched Off Residency", locality=town, active=False)
    hidden_town = factories.make_locality(db, "Unchecked Town", verified=False)
    factories.make_society(db, "Inside Unchecked Town", locality=hidden_town)
    off_town = factories.make_locality(db, "Switched Off Town", active=False)
    factories.make_society(db, "Inside Switched Off Town", locality=off_town)

    societies = api.get("/api/v1/societies").json()
    localities = api.get("/api/v1/localities").json()

    assert [item["name"] for item in societies] == ["Shown Residency"]
    assert [(item["name"], item["society_count"]) for item in localities] == [("Public Town", 1)]


def test_a_hidden_society_cannot_be_opened_directly(api: TestClient, db: Session) -> None:
    shown = factories.make_society(db, "Shown")
    hidden = factories.make_society(db, "Hidden", verified=False)

    assert api.get(f"/api/v1/societies/{shown.id}").status_code == 200
    unverified = api.get(f"/api/v1/societies/{hidden.id}")
    missing = api.get("/api/v1/societies/00000000-0000-0000-0000-000000000000")
    assert unverified.status_code == missing.status_code == 404
    assert unverified.json() == missing.json()


def test_public_records_never_reveal_private_details(api: TestClient, db: Session) -> None:
    society = factories.make_society(db, "Private Details Residency")
    society.source_note = "Seen on a secret-source page"
    db.flush()

    for text in (
        api.get("/api/v1/societies").text,
        api.get(f"/api/v1/societies/{society.id}").text,
        api.get("/api/v1/localities").text,
    ):
        assert "Private Lane" not in text  # the address
        assert "secret-source" not in text
        assert "verified_by" not in text
        assert "latitude" not in text


def test_societies_can_be_searched_and_filtered(api: TestClient, db: Session) -> None:
    north = factories.make_locality(db, "North Town")
    south = factories.make_locality(db, "South Town")
    factories.make_society(db, "Lakeside Residency", locality=north)
    factories.make_society(db, "Maple Court", locality=north)
    factories.make_society(db, "Lakeview Towers", locality=south)

    def names(**params: str) -> list[str]:
        return [item["name"] for item in api.get("/api/v1/societies", params=params).json()]

    assert names(q="lake") == ["Lakeside Residency", "Lakeview Towers"]
    assert names(q="LAKE", locality_id=str(south.id)) == ["Lakeview Towers"]
    assert names(locality_id=str(north.id)) == ["Lakeside Residency", "Maple Court"]
    assert names(q="south town") == ["Lakeview Towers"]  # by locality name
    assert names(q="nothing like this") == []
    assert names(q="%") == []  # a wildcard character is just a character


def test_results_are_paged(api: TestClient, db: Session) -> None:
    town = factories.make_locality(db, "Paged Town")
    for letter in "ABCDE":
        factories.make_society(db, f"{letter} Paged Residency", locality=town)

    first = api.get("/api/v1/societies", params={"limit": 2}).json()
    second = api.get("/api/v1/societies", params={"limit": 2, "offset": 2}).json()

    assert [item["name"] for item in first] == ["A Paged Residency", "B Paged Residency"]
    assert [item["name"] for item in second] == ["C Paged Residency", "D Paged Residency"]
    assert api.get("/api/v1/societies", params={"limit": 101}).status_code == 422


# --- Who can change the directory ---------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/localities"),
        ("post", "/localities"),
        ("get", "/societies"),
        ("post", "/societies"),
        ("post", "/societies/00000000-0000-0000-0000-000000000000/verify"),
        ("post", "/localities/00000000-0000-0000-0000-000000000000/deactivate"),
    ],
)
def test_members_and_visitors_cannot_manage_the_directory(
    api: TestClient, new_client: Callable[[], TestClient], method: str, path: str
) -> None:
    visitor = new_client()
    assert getattr(visitor, method)(f"{ADMIN}{path}").status_code == 401

    headers = sign_up(api)
    response = getattr(api, method)(f"{ADMIN}{path}", headers=headers)
    assert response.status_code == 403


def test_admin_changes_need_the_csrf_token(
    admin: tuple[TestClient, dict[str, str]],
) -> None:
    client, _headers = admin

    response = client.post(f"{ADMIN}/localities", json={"name": "X", "city": "Y", "state": "Z"})

    assert response.status_code == 403


# --- Creating, duplicates and editing ------------------------------------


def _create_locality(client: TestClient, headers: dict[str, str], **fields: str) -> dict:
    body = {"name": "Potheri", "city": "Chengalpattu district", "state": "Tamil Nadu"} | fields
    response = client.post(f"{ADMIN}/localities", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_society(
    client: TestClient, headers: dict[str, str], locality_id: str, **fields: str
) -> dict:
    body = {"locality_id": locality_id, "name": "Sample Heights"} | fields
    response = client.post(f"{ADMIN}/societies", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_new_records_start_unverified_and_hidden(
    admin: tuple[TestClient, dict[str, str]], api: TestClient
) -> None:
    client, headers = admin

    locality = _create_locality(client, headers, source_note="Named in the PRD")
    society = _create_society(client, headers, locality["id"], community_type="APARTMENT_COMPLEX")

    assert locality["verification_status"] == "UNVERIFIED"
    assert locality["is_public"] is False
    assert society["verification_status"] == "UNVERIFIED"
    assert society["is_public"] is False
    assert api.get("/api/v1/societies").json() == []
    assert locality["history"][0]["action"] == "CREATED"
    assert locality["history"][0]["actor_email"] == "admin@example.com"


@pytest.mark.parametrize("variant", ["potheri", "  POTHERI ", "Potheri.", "Pot-heri"])
def test_duplicate_localities_are_refused_whatever_the_spelling_style(
    admin: tuple[TestClient, dict[str, str]], db: Session, variant: str
) -> None:
    client, headers = admin
    _create_locality(client, headers)

    response = client.post(
        f"{ADMIN}/localities",
        json={"name": variant, "city": "Chengalpattu district", "state": "Tamil Nadu"},
        headers=headers,
    )

    if variant == "Pot-heri":
        # Not the same normalised name: a real spelling difference a person
        # must judge. This is why every new record starts unverified.
        assert response.status_code == 201
    else:
        assert response.status_code == 409
        assert "already in the directory" in response.json()["error"]["message"]


def test_a_society_cannot_be_added_twice_even_in_another_locality(
    admin: tuple[TestClient, dict[str, str]],
) -> None:
    client, headers = admin
    potheri = _create_locality(client, headers)
    srm_nagar = _create_locality(client, headers, name="SRM Nagar")
    _create_society(client, headers, potheri["id"], name="Abode Valley")

    response = client.post(
        f"{ADMIN}/societies",
        json={"locality_id": srm_nagar["id"], "name": "abode-valley"},
        headers=headers,
    )

    assert response.status_code == 409
    assert "in Potheri" in response.json()["error"]["message"]


def test_renaming_into_a_duplicate_is_refused(
    admin: tuple[TestClient, dict[str, str]],
) -> None:
    client, headers = admin
    town = _create_locality(client, headers)
    _create_society(client, headers, town["id"], name="First Heights")
    second = _create_society(client, headers, town["id"], name="Second Heights")

    response = client.patch(
        f"{ADMIN}/societies/{second['id']}", json={"name": "FIRST heights"}, headers=headers
    )

    assert response.status_code == 409


def test_a_society_needs_an_existing_locality(admin: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = admin

    response = client.post(
        f"{ADMIN}/societies",
        json={"locality_id": "00000000-0000-0000-0000-000000000000", "name": "Nowhere Heights"},
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"name": "", "city": "C", "state": "S"},
        {"name": "   ", "city": "C", "state": "S"},
        {"name": "X", "city": "C", "state": "S", "postal_code": "60320"},
        {"name": "X", "city": "C", "state": "S", "description": "d" * 2001},
        {"name": "!!!", "city": "C", "state": "S"},
    ],
)
def test_invalid_localities_are_refused(
    admin: tuple[TestClient, dict[str, str]], body: dict
) -> None:
    client, headers = admin

    response = client.post(f"{ADMIN}/localities", json=body, headers=headers)

    assert response.status_code == 422


def test_editing_a_verified_societys_core_facts_unverifies_it(
    admin: tuple[TestClient, dict[str, str]],
) -> None:
    client, headers = admin
    town = _create_locality(client, headers)
    society = _create_society(client, headers, town["id"], community_type="APARTMENT_COMPLEX")
    client.post(
        f"{ADMIN}/societies/{society['id']}/verify",
        json={"note": "Visited on 20 Nov"},
        headers=headers,
    )

    # A description change keeps the verification...
    described = client.patch(
        f"{ADMIN}/societies/{society['id']}",
        json={"description": "Off GST Road.", "note": "Added a description"},
        headers=headers,
    ).json()
    assert described["verification_status"] == "VERIFIED"

    # ...but a new name has not been confirmed, so it is unverified again.
    renamed = client.patch(
        f"{ADMIN}/societies/{society['id']}",
        json={"name": "Sample Heights Phase 2"},
        headers=headers,
    ).json()
    assert renamed["verification_status"] == "UNVERIFIED"
    assert renamed["verified_by_email"] is None
    last = renamed["history"][-1]
    assert last["action"] == "UPDATED"
    assert last["changes"]["name"] == {"from": "Sample Heights", "to": "Sample Heights Phase 2"}
    assert last["changes"]["verification_status"] == {"from": "VERIFIED", "to": "UNVERIFIED"}


def test_a_required_field_cannot_be_cleared(admin: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = admin
    town = _create_locality(client, headers)

    response = client.patch(
        f"{ADMIN}/localities/{town['id']}", json={"name": None}, headers=headers
    )

    assert response.status_code == 422


# --- Verifying and activating --------------------------------------------


def test_publishing_a_society_takes_both_records_verified(
    admin: tuple[TestClient, dict[str, str]], api: TestClient
) -> None:
    client, headers = admin
    town = _create_locality(client, headers)
    society = _create_society(client, headers, town["id"])

    # A society cannot be verified until its type is known.
    no_type = client.post(
        f"{ADMIN}/societies/{society['id']}/verify", json={"note": "Visited"}, headers=headers
    )
    assert no_type.status_code == 422
    client.patch(
        f"{ADMIN}/societies/{society['id']}",
        json={"community_type": "APARTMENT_COMPLEX"},
        headers=headers,
    )

    # A verification must say how it was confirmed.
    no_note = client.post(f"{ADMIN}/societies/{society['id']}/verify", json={}, headers=headers)
    assert no_note.status_code == 422

    verified = client.post(
        f"{ADMIN}/societies/{society['id']}/verify",
        json={"note": "Visited on 20 Nov; spoke to the security office."},
        headers=headers,
    ).json()
    assert verified["verification_status"] == "VERIFIED"
    assert verified["verified_by_email"] == "admin@example.com"
    # Still hidden: its locality is not verified yet.
    assert verified["is_public"] is False
    assert api.get("/api/v1/societies").json() == []

    client.post(
        f"{ADMIN}/localities/{town['id']}/verify",
        json={"note": "Area name confirmed with local residents."},
        headers=headers,
    )
    assert [item["name"] for item in api.get("/api/v1/societies").json()] == ["Sample Heights"]


def test_deactivating_hides_a_record_and_keeps_choices(
    admin: tuple[TestClient, dict[str, str]], api: TestClient, db: Session
) -> None:
    client, headers = admin
    society = factories.make_society(db, "Popular Residency")
    member_headers = sign_up(api)
    api.put("/api/v1/me/societies", json={"society_ids": [str(society.id)]}, headers=member_headers)

    off = client.post(
        f"{ADMIN}/societies/{society.id}/deactivate",
        json={"note": "Reported closed for renovation"},
        headers=headers,
    )
    assert off.status_code == 200
    assert off.json()["chosen_by_count"] == 1
    assert api.get("/api/v1/societies").json() == []
    # The member's choice is kept, marked unavailable.
    [saved] = api.get("/api/v1/me").json()["societies"]
    assert saved["available"] is False

    # Doing it twice is refused; switching back on restores it.
    again = client.post(f"{ADMIN}/societies/{society.id}/deactivate", json={}, headers=headers)
    assert again.status_code == 409
    client.post(f"{ADMIN}/societies/{society.id}/activate", json={}, headers=headers)
    assert api.get("/api/v1/me").json()["societies"][0]["available"] is True


def test_every_change_is_in_the_history(
    admin: tuple[TestClient, dict[str, str]],
) -> None:
    client, headers = admin
    town = _create_locality(client, headers)
    base = f"{ADMIN}/localities/{town['id']}"
    client.post(f"{base}/verify", json={"note": "Confirmed"}, headers=headers)
    client.post(f"{base}/unverify", json={"note": "Spelling in doubt"}, headers=headers)
    client.post(f"{base}/deactivate", json={"note": "Pausing"}, headers=headers)
    client.post(f"{base}/activate", json={}, headers=headers)

    history = client.get(base).json()["history"]

    assert [event["action"] for event in history] == [
        "CREATED",
        "VERIFIED",
        "UNVERIFIED",
        "DEACTIVATED",
        "ACTIVATED",
    ]
    assert history[2]["note"] == "Spelling in doubt"
    assert all(event["actor_email"] == "admin@example.com" for event in history)


def test_admins_see_everything_with_filters(
    admin: tuple[TestClient, dict[str, str]], db: Session
) -> None:
    client, _headers = admin
    factories.make_society(db, "Shown Admin Residency")
    factories.make_society(db, "Unchecked Admin Residency", verified=False)

    everything = client.get(f"{ADMIN}/societies", params={"q": "admin residency"}).json()
    unverified = client.get(
        f"{ADMIN}/societies", params={"q": "admin residency", "verification_status": "UNVERIFIED"}
    ).json()

    assert {item["name"] for item in everything} == {
        "Shown Admin Residency",
        "Unchecked Admin Residency",
    }
    assert [item["name"] for item in unverified] == ["Unchecked Admin Residency"]
    assert everything[0]["address"] == "12 Private Lane, Flat 4B"  # admins do see this


# --- Importing candidates -------------------------------------------------


def _candidates() -> dict:
    return json.loads(Path(DEFAULT_FILE).read_text(encoding="utf-8"))


def test_the_candidate_file_is_well_formed() -> None:
    data = _candidates()
    locality_names = {entry["name"] for entry in data["localities"]}

    assert {"Potheri", "SRM Nagar", "Kattankulathur", "Guduvanchery"} <= locality_names
    for entry in data["societies"]:
        assert entry["locality"] in locality_names
        assert entry["sources"], f"{entry['name']} has no source"
        # Descriptions are written by whoever verifies the record, not invented.
        assert "description" not in entry


def test_importing_adds_unverified_records_and_can_be_repeated(
    db: Session, api: TestClient
) -> None:
    data = _candidates()

    first = directory_service.import_candidates(db, data, source_name="candidates.json")
    second = directory_service.import_candidates(db, data, source_name="candidates.json")

    assert len(first.societies_created) == len(data["societies"])
    assert second.localities_created == second.societies_created == []
    imported = db.scalars(select(Society)).all()
    assert len(imported) == len(data["societies"])
    assert all(item.verification_status == DirectoryStatus.UNVERIFIED for item in imported)
    assert all(item.source_note and "http" in item.source_note for item in imported)
    # Nothing imported is visible to students.
    assert api.get("/api/v1/societies").json() == []
    assert api.get("/api/v1/localities").json() == []


def test_importing_never_overwrites_an_admins_work(db: Session) -> None:
    data = _candidates()
    directory_service.import_candidates(db, data, source_name="candidates.json")
    admin = factories.make_admin(db)
    society = db.scalar(select(Society).where(Society.name == data["societies"][0]["name"]))
    assert society is not None
    directory_service.update_society(
        db, society, {"description": "Written by an admin"}, actor=admin, note=None
    )

    directory_service.import_candidates(db, data, source_name="candidates.json")

    db.refresh(society)
    assert society.description == "Written by an admin"


def test_importing_fills_a_missing_locality_source_and_records_it(db: Session) -> None:
    data = _candidates()
    first, second = data["localities"][0], data["localities"][1]
    # Two localities that existed before the import (as the old samples did):
    # one without any source note, one whose note an admin already wrote.
    bare = Locality(name=first["name"], city=first["city"], state=first["state"])
    noted = Locality(
        name=second["name"], city=second["city"], state=second["state"], source_note="Mine"
    )
    db.add_all([bare, noted])
    db.flush()

    directory_service.import_candidates(db, data, source_name="candidates.json")
    directory_service.import_candidates(db, data, source_name="candidates.json")

    db.refresh(bare)
    db.refresh(noted)
    assert bare.source_note and first["sources"][0] in bare.source_note
    assert noted.source_note == "Mine"
    # The fill-in is in the history, once, however often the import runs.
    events = db.scalars(select(DirectoryEvent).where(DirectoryEvent.locality_id == bare.id)).all()
    assert [(event.action.value, list(event.changes or {})) for event in events] == [
        ("UPDATED", ["source_note"])
    ]
    assert not db.scalars(
        select(DirectoryEvent).where(DirectoryEvent.locality_id == noted.id)
    ).all()


# --- Retiring the development samples -------------------------------------


def _sample(db: Session, name: str, locality: Locality) -> Society:
    society = Society(
        locality_id=locality.id,
        name=f"{name}{directory_service.SAMPLE_NAME_SUFFIX}",
        description=directory_service.SAMPLE_DESCRIPTION,
    )
    db.add(society)
    db.flush()
    return society


def test_retiring_samples_deletes_unused_ones_and_keeps_chosen_ones(db: Session) -> None:
    town = factories.make_locality(db, "Sample Town")
    unused = _sample(db, "Unused", town)
    chosen = _sample(db, "Chosen", town)
    real = factories.make_society(db, "Real Residency", locality=town)
    member = factories.make_user(db)
    db.add(UserSocietyPreference(user_id=member.id, society_id=chosen.id, priority=1))
    db.flush()
    unused_id = unused.id

    report = directory_service.retire_sample_societies(db)

    assert report.deleted == ["Unused (sample)"]
    assert report.deactivated == {"Chosen (sample)": 1}
    assert db.get(Society, unused_id) is None
    db.refresh(chosen)
    assert chosen.is_active is False
    # The member's choice is still there.
    assert db.scalar(
        select(UserSocietyPreference).where(UserSocietyPreference.society_id == chosen.id)
    )
    db.refresh(real)
    assert real.is_active is True
    event = db.scalar(select(DirectoryEvent).where(DirectoryEvent.society_id == chosen.id))
    assert event is not None and event.actor_id is None  # done by a script

    # Running it again changes nothing more.
    again = directory_service.retire_sample_societies(db)
    assert again.deleted == []


def test_the_fixture_seed_refuses_a_real_database(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.scripts import seed_test_fixtures

    monkeypatch.setattr(get_settings(), "postgres_db", "roomie")

    assert seed_test_fixtures.main() == 1
