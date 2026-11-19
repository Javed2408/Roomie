"""Tests for the profile, roommate preferences and preferred societies."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests import factories
from tests.helpers import PASSWORD, log_in, sign_up

pytestmark = pytest.mark.integration

PROFILE = {
    "full_name": "Ananya Rao",
    "college_name": "SRM IST",
    "course": "B.Tech",
    "department": "Computer Science",
    "academic_year": 2,
    "bio": "Tidy and friendly.",
    "gender": "WOMAN",
    "gender_visible": False,
}
PREFERENCES = {
    "min_budget": 8000,
    "max_budget": 12000,
    "move_in_date": "2027-01-05",
    "room_type": "PRIVATE_ROOM",
    "food_preference": "VEGETARIAN",
    "sleep_schedule": "NIGHT_OWL",
}


def test_a_new_account_starts_empty(api: TestClient) -> None:
    sign_up(api)

    account = api.get("/api/v1/me").json()

    assert account["profile"] is None
    assert account["preferences"] is None
    assert account["societies"] == []
    assert account["verifications"]["identity"]["status"] == "NOT_SUBMITTED"
    assert account["verifications"]["student"]["status"] == "NOT_SUBMITTED"


def test_creating_then_updating_a_profile(api: TestClient) -> None:
    headers = sign_up(api)

    created = api.put("/api/v1/me/profile", json=PROFILE, headers=headers)
    assert created.status_code == 200
    assert created.json()["profile"] == PROFILE | {"profile_completed": False, "photo_url": None}

    updated = api.put(
        "/api/v1/me/profile", json=PROFILE | {"bio": "", "academic_year": 3}, headers=headers
    )
    assert updated.json()["profile"]["academic_year"] == 3
    assert updated.json()["profile"]["bio"] is None  # blank means "not provided"


def test_everything_persists_after_logging_out_and_back_in(
    api: TestClient, new_client: Callable[[], TestClient], db: Session
) -> None:
    first, second = factories.make_society(db, "Lakeside"), factories.make_society(db, "Maple")
    headers = sign_up(api, "student@example.com")
    api.put("/api/v1/me/profile", json=PROFILE, headers=headers)
    api.put("/api/v1/me/preferences", json=PREFERENCES, headers=headers)
    api.put(
        "/api/v1/me/societies",
        json={"society_ids": [str(second.id), str(first.id)]},
        headers=headers,
    )
    api.post("/api/v1/auth/logout", headers=headers)

    another_browser = new_client()
    log_in(another_browser, "student@example.com", PASSWORD)
    account = another_browser.get("/api/v1/me").json()

    assert account["profile"]["full_name"] == "Ananya Rao"
    assert account["preferences"]["min_budget"] == 8000
    assert account["preferences"]["move_in_date"] == "2027-01-05"
    assert account["preferences"]["smoking_preference"] is None  # never answered
    # The order chosen is the order returned.
    assert [(item["society"]["name"], item["priority"]) for item in account["societies"]] == [
        ("Maple", 1),
        ("Lakeside", 2),
    ]


@pytest.mark.parametrize(
    "bad_profile",
    [
        PROFILE | {"full_name": "   "},
        PROFILE | {"college_name": ""},
        PROFILE | {"academic_year": 12},
        PROFILE | {"bio": "x" * 501},
        PROFILE | {"gender": "SOMETHING_ELSE"},
    ],
)
def test_invalid_profiles_are_refused(api: TestClient, bad_profile: dict) -> None:
    headers = sign_up(api)

    response = api.put("/api/v1/me/profile", json=bad_profile, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert api.get("/api/v1/me").json()["profile"] is None


@pytest.mark.parametrize(
    "bad_preferences",
    [
        {"min_budget": 12000, "max_budget": 9000},
        {"min_budget": 10},
        {"max_budget": 5_000_000},
        {"room_type": "CASTLE"},
        {"move_in_date": "next week"},
    ],
)
def test_invalid_preferences_are_refused(api: TestClient, bad_preferences: dict) -> None:
    headers = sign_up(api)

    response = api.put("/api/v1/me/preferences", json=bad_preferences, headers=headers)

    assert response.status_code == 422
    assert api.get("/api/v1/me").json()["preferences"] is None


def test_society_choices_can_be_replaced_and_reordered(api: TestClient, db: Session) -> None:
    a, b, c = (factories.make_society(db, name) for name in ("A", "B", "C"))
    headers = sign_up(api)

    api.put("/api/v1/me/societies", json={"society_ids": [str(a.id), str(b.id)]}, headers=headers)
    response = api.put(
        "/api/v1/me/societies", json={"society_ids": [str(c.id), str(a.id)]}, headers=headers
    )

    assert [item["society"]["name"] for item in response.json()["societies"]] == ["C", "A"]


def test_bad_society_choices_are_refused(api: TestClient, db: Session) -> None:
    active = factories.make_society(db, "Active")
    inactive = factories.make_society(db, "Closed", active=False)
    unverified = factories.make_society(db, "Not Checked", verified=False)
    hidden_area = factories.make_society(
        db, "In Hidden Area", locality=factories.make_locality(db, verified=False)
    )
    headers = sign_up(api)
    url = "/api/v1/me/societies"
    six = [str(factories.make_society(db).id) for _ in range(6)]

    responses = [
        api.put(url, json={"society_ids": [str(inactive.id)]}, headers=headers),
        api.put(url, json={"society_ids": [str(unverified.id)]}, headers=headers),
        api.put(url, json={"society_ids": [str(hidden_area.id)]}, headers=headers),
        api.put(url, json={"society_ids": [str(active.id)] * 2}, headers=headers),
        api.put(url, json={"society_ids": six}, headers=headers),
        api.put(
            url, json={"society_ids": ["00000000-0000-0000-0000-000000000000"]}, headers=headers
        ),
    ]

    assert [response.status_code for response in responses] == [422] * 6
    assert api.get("/api/v1/me").json()["societies"] == []


def test_a_society_that_leaves_the_directory_stays_listed_but_unavailable(
    api: TestClient, db: Session
) -> None:
    """Nobody's saved choices are deleted behind their back."""
    kept, retired = factories.make_society(db, "Kept"), factories.make_society(db, "Retired")
    headers = sign_up(api)
    api.put("/api/v1/me/profile", json=PROFILE, headers=headers)
    api.put("/api/v1/me/preferences", json=PREFERENCES, headers=headers)
    api.put(
        "/api/v1/me/societies",
        json={"society_ids": [str(retired.id), str(kept.id)]},
        headers=headers,
    )

    retired.is_active = False
    db.flush()

    societies = api.get("/api/v1/me").json()["societies"]
    assert [(item["society"]["name"], item["available"]) for item in societies] == [
        ("Retired", False),
        ("Kept", True),
    ]
    # Still publishable: one society that is in the directory remains.
    assert api.post("/api/v1/me/profile/publish", headers=headers).status_code == 200

    # Once the last one goes, the profile no longer meets the rules.
    kept.is_active = False
    db.flush()
    blocked = api.post("/api/v1/me/profile/publish", headers=headers)
    assert blocked.status_code == 422
    assert blocked.json()["error"]["details"] == ["Choose at least one society."]


def test_a_profile_can_only_be_published_when_complete(api: TestClient, db: Session) -> None:
    society = factories.make_society(db)
    headers = sign_up(api)
    publish = "/api/v1/me/profile/publish"

    nothing_yet = api.post(publish, headers=headers)
    assert nothing_yet.status_code == 422
    assert nothing_yet.json()["error"]["details"] == [
        "Add your name and college.",
        "Set your monthly budget.",
        "Choose a move-in date.",
        "Choose at least one society.",
    ]

    api.put("/api/v1/me/profile", json=PROFILE, headers=headers)
    api.put("/api/v1/me/preferences", json=PREFERENCES, headers=headers)
    still_missing = api.post(publish, headers=headers)
    assert still_missing.json()["error"]["details"] == ["Choose at least one society."]

    api.put("/api/v1/me/societies", json={"society_ids": [str(society.id)]}, headers=headers)
    published = api.post(publish, headers=headers)
    assert published.status_code == 200
    assert published.json()["profile"]["profile_completed"] is True


def test_removing_something_required_un_completes_the_profile(api: TestClient, db: Session) -> None:
    society = factories.make_society(db)
    headers = sign_up(api)
    api.put("/api/v1/me/profile", json=PROFILE, headers=headers)
    api.put("/api/v1/me/preferences", json=PREFERENCES, headers=headers)
    api.put("/api/v1/me/societies", json={"society_ids": [str(society.id)]}, headers=headers)
    api.post("/api/v1/me/profile/publish", headers=headers)

    response = api.put("/api/v1/me/societies", json={"society_ids": []}, headers=headers)

    assert response.json()["profile"]["profile_completed"] is False


def test_one_person_cannot_see_or_change_anothers_profile(
    api: TestClient, new_client: Callable[[], TestClient]
) -> None:
    """Every route acts on "me"; there is no way to name another user."""
    first_headers = sign_up(api, "first@example.com")
    api.put("/api/v1/me/profile", json=PROFILE, headers=first_headers)
    second = new_client()
    second_headers = sign_up(second, "second@example.com")

    second.put(
        "/api/v1/me/profile",
        json=PROFILE | {"full_name": "Someone Else"},
        headers=second_headers,
    )

    assert api.get("/api/v1/me").json()["profile"]["full_name"] == "Ananya Rao"
    assert second.get("/api/v1/me").json()["profile"]["full_name"] == "Someone Else"
    assert second.get("/api/v1/me").json()["user"]["email"] == "second@example.com"


def test_the_account_never_exposes_private_fields(api: TestClient, db: Session) -> None:
    headers = sign_up(api)
    api.put("/api/v1/me/profile", json=PROFILE, headers=headers)

    text = api.get("/api/v1/me").text

    for private in ("password", "date_of_birth", "token", "storage_key", "argon2"):
        assert private not in text
