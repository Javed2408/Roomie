"""Unit tests for the compatibility scoring engine (no database needed)."""

import uuid
from dataclasses import replace
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.models.enums import (
    CleanlinessLevel,
    FoodPreference,
    GuestFrequency,
    HabitFrequency,
    RoomType,
    SleepSchedule,
    SocialPreference,
)
from app.services.compatibility import (
    DEFAULT_WEIGHTS,
    AreaOverlap,
    CompatibilityInput,
    Factor,
    SocietyChoice,
    calculate,
    combine,
    format_inr,
    round_half_up,
    score_budget,
    score_food,
    score_lifestyle,
    score_move_in,
    score_room,
    score_societies,
)

# --- Building inputs ----------------------------------------------------------

POTHERI, GUDUVANCHERY = uuid.uuid4(), uuid.uuid4()
_SOCIETY_IDS: dict[str, uuid.UUID] = {}


def choice(
    name: str,
    priority: int = 1,
    *,
    locality: str = "Potheri",
    is_public: bool = True,
) -> SocietyChoice:
    """The same name always gets the same id, so two people can share it."""
    return SocietyChoice(
        society_id=_SOCIETY_IDS.setdefault(name, uuid.uuid4()),
        society_name=name,
        locality_id=POTHERI if locality == "Potheri" else GUDUVANCHERY,
        locality_name=locality,
        priority=priority,
        is_public=is_public,
    )


def person(**answers: object) -> CompatibilityInput:
    return CompatibilityInput(**answers)  # type: ignore[arg-type]


def budget(low: int, high: int) -> CompatibilityInput:
    return person(min_budget=low, max_budget=high)


FULL = CompatibilityInput(
    min_budget=8000,
    max_budget=12000,
    move_in_date=date(2027, 1, 10),
    room_type=RoomType.PRIVATE_ROOM,
    food_preference=FoodPreference.VEGETARIAN,
    smoking=HabitFrequency.NEVER,
    drinking=HabitFrequency.NEVER,
    sleep_schedule=SleepSchedule.EARLY_BIRD,
    cleanliness=CleanlinessLevel.TIDY,
    social=SocialPreference.QUIET,
    guests=GuestFrequency.RARELY,
    societies=(choice("Lancor Abode Valley", 1), choice("VGN Tranquil", 2)),
)


# --- Helpers --------------------------------------------------------------------


def test_rounding_is_half_up_and_rupees_use_indian_grouping() -> None:
    assert [round_half_up(value) for value in (84.5, 85.5, 84.49)] == [85, 86, 84]
    assert format_inr(9500) == "₹9,500"
    assert format_inr(100000) == "₹1,00,000"
    assert format_inr(12500000) == "₹1,25,00,000"


# --- Budget ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ((8000, 12000), (8000, 12000), 100),  # identical
        ((8000, 12000), (9000, 10000), 100),  # the narrower range fits inside
        ((8000, 12000), (10000, 14000), 85),  # half of the narrower range shared
        ((8000, 10000), (10000, 12000), 70),  # they only meet at one amount
        ((8000, 10000), (11000, 13000), 40),  # ₹1,000 apart: 10% of ₹10,000
        ((8000, 10000), (13000, 15000), 0),  # 30% apart or more
        ((9000, 9000), (9000, 9000), 100),  # exact amounts that agree
    ],
)
def test_budget_compares_ranges(
    first: tuple[int, int], second: tuple[int, int], expected: int
) -> None:
    assert score_budget(budget(*first), budget(*second)).score == expected


def test_budget_explanations_name_the_shared_or_missing_amount() -> None:
    overlap = score_budget(budget(8000, 12000), budget(10000, 14000))
    apart = score_budget(budget(8000, 10000), budget(11000, 13000))

    assert overlap.explanation == "Your budgets overlap between ₹10,000 and ₹12,000 a month."
    assert apart.explanation == "Your budgets do not overlap: they are ₹1,000 apart."


@pytest.mark.parametrize(
    "incomplete",
    [person(), person(min_budget=8000), person(max_budget=12000)],
)
def test_budget_is_unavailable_when_either_side_is_missing(incomplete: CompatibilityInput) -> None:
    result = score_budget(budget(8000, 12000), incomplete)

    assert result.score is None
    assert result.explanation == "Not enough information to compare budgets."


# --- Societies -------------------------------------------------------------------


def test_same_first_choice_scores_highest() -> None:
    a = person(societies=(choice("Lancor Abode Valley", 1), choice("VGN Tranquil", 2)))
    b = person(societies=(choice("Lancor Abode Valley", 1),))

    scored, area, shared = score_societies(a, b)

    assert scored.score == 100
    assert area == AreaOverlap.SAME_SOCIETY
    assert shared == ("Lancor Abode Valley",)
    assert scored.explanation == "You both chose Lancor Abode Valley as your first choice."


def test_lower_ranks_score_less_but_never_below_sixty() -> None:
    a = person(societies=(choice("A", 1), choice("B", 2), choice("Shared", 3)))
    b = person(societies=(choice("C", 1), choice("Shared", 2)))
    far = person(societies=tuple(choice(name, rank) for rank, name in enumerate("ABCDE", 1)))
    far_b = person(societies=tuple(choice(name, rank) for rank, name in enumerate("FGHIE", 1)))

    assert score_societies(a, b)[0].score == 70  # 100 - 20 (3rd) - 10 (2nd)
    assert score_societies(far, far_b)[0].score == 60  # both 5th: floor


def test_the_best_shared_society_counts_and_all_are_named() -> None:
    a = person(societies=(choice("Alpha", 1), choice("Beta", 2)))
    b = person(societies=(choice("Beta", 1), choice("Alpha", 2)))

    scored, _, shared = score_societies(a, b)

    assert scored.score == 90
    assert shared == ("Alpha", "Beta")
    assert scored.explanation == "You both chose Alpha and Beta."


def test_same_area_different_societies_scores_forty() -> None:
    a = person(societies=(choice("Lancor Abode Valley"),))
    b = person(societies=(choice("DAC Urban Park"),))

    scored, area, _ = score_societies(a, b)

    assert scored.score == 40
    assert area == AreaOverlap.SAME_LOCALITY
    assert "Potheri" in scored.explanation


def test_no_overlap_at_all_scores_zero() -> None:
    a = person(societies=(choice("Lancor Abode Valley"),))
    b = person(societies=(choice("Lancor Lumina", locality="Guduvanchery"),))

    scored, area, _ = score_societies(a, b)

    assert (scored.score, area) == (0, AreaOverlap.NONE)


def test_societies_that_are_not_public_never_count() -> None:
    # They "share" a society, but it is unverified or switched off.
    hidden = choice("Retired Residency", 1, is_public=False)
    a = person(societies=(hidden, choice("Lancor Abode Valley", 2)))
    b = person(societies=(hidden, choice("Lancor Lumina", 2, locality="Guduvanchery")))

    scored, area, shared = score_societies(a, b)

    assert scored.score == 0
    assert area == AreaOverlap.NONE
    assert shared == ()


def test_when_one_side_has_no_public_society_the_factor_is_unavailable() -> None:
    a = person(societies=(choice("Lancor Abode Valley"),))
    only_hidden = person(societies=(choice("Lancor Abode Valley", is_public=False),))

    for other in (only_hidden, person()):
        scored, area, _ = score_societies(a, other)
        assert scored.score is None
        assert area == AreaOverlap.UNKNOWN


def test_a_retired_first_choice_moves_the_second_choice_up() -> None:
    a = person(societies=(choice("Retired", 1, is_public=False), choice("Shared", 2)))
    b = person(societies=(choice("Shared", 1),))

    assert score_societies(a, b)[0].score == 100


# --- Lifestyle --------------------------------------------------------------------


def test_identical_habits_score_full_marks() -> None:
    result = score_lifestyle(FULL, FULL)

    assert result.score == 100
    assert result.explanation.startswith("In common: early riser, tidy, prefers a quiet home")
    assert "Based on" not in result.explanation  # all six were compared


def test_opposite_habits_score_zero_and_are_named() -> None:
    opposite = replace(
        FULL,
        smoking=HabitFrequency.REGULARLY,
        drinking=HabitFrequency.REGULARLY,
        sleep_schedule=SleepSchedule.NIGHT_OWL,
        cleanliness=CleanlinessLevel.RELAXED,
        social=SocialPreference.SOCIAL,
        guests=GuestFrequency.OFTEN,
    )
    tidy_but_not_very = replace(FULL, cleanliness=CleanlinessLevel.VERY_TIDY)

    result = score_lifestyle(replace(FULL, cleanliness=CleanlinessLevel.VERY_TIDY), opposite)

    assert result.score == 0
    assert result.explanation.startswith("Different sleep schedule, tidiness,")
    # One step apart on one habit out of six: (5 x 100 + 50) / 6.
    assert score_lifestyle(FULL, tidy_but_not_very).score == 92


def test_a_flexible_sleeper_partly_suits_anyone() -> None:
    a = person(sleep_schedule=SleepSchedule.FLEXIBLE)
    b = person(sleep_schedule=SleepSchedule.NIGHT_OWL)

    assert score_lifestyle(a, b).score == 75


def test_only_habits_both_answered_are_compared() -> None:
    a = person(smoking=HabitFrequency.NEVER, sleep_schedule=SleepSchedule.EARLY_BIRD)
    b = person(smoking=HabitFrequency.NEVER, cleanliness=CleanlinessLevel.TIDY)

    result = score_lifestyle(a, b)

    assert result.score == 100
    assert result.explanation == "In common: non-smoker. Based on 1 of 6 habits."


def test_lifestyle_is_unavailable_with_no_habit_in_common() -> None:
    a = person(smoking=HabitFrequency.NEVER)
    b = person(drinking=HabitFrequency.NEVER)

    assert score_lifestyle(a, b).score is None


# --- Move-in date -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (0, 100),
        (7, 100),
        (8, 85),
        (14, 85),
        (15, 70),
        (30, 70),
        (31, 40),
        (60, 40),
        (61, 20),
        (90, 20),
        (91, 0),
        (365, 0),
    ],
)
def test_move_in_score_falls_with_the_gap(days: int, expected: int) -> None:
    start = date(2027, 1, 10)
    a = person(move_in_date=start)
    b = person(move_in_date=start + timedelta(days=days))

    assert score_move_in(a, b).score == expected
    assert score_move_in(b, a).score == expected


def test_move_in_explanations() -> None:
    day = date(2027, 1, 10)

    same = score_move_in(person(move_in_date=day), person(move_in_date=day))
    one = score_move_in(person(move_in_date=day), person(move_in_date=day + timedelta(days=1)))
    missing = score_move_in(person(move_in_date=day), person())

    assert same.explanation == "You want to move in on the same date."
    assert one.explanation == "Your move-in dates are 1 day apart."
    assert missing.score is None


# --- Room type -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        (RoomType.PRIVATE_ROOM, RoomType.PRIVATE_ROOM, 100),
        (RoomType.SHARED_ROOM, RoomType.SHARED_ROOM, 100),
        (RoomType.NO_PREFERENCE, RoomType.NO_PREFERENCE, 100),
        (RoomType.PRIVATE_ROOM, RoomType.NO_PREFERENCE, 80),
        (RoomType.SHARED_ROOM, RoomType.NO_PREFERENCE, 80),
        (RoomType.PRIVATE_ROOM, RoomType.SHARED_ROOM, 30),
    ],
)
def test_room_type(first: RoomType, second: RoomType, expected: int) -> None:
    assert score_room(person(room_type=first), person(room_type=second)).score == expected
    assert score_room(person(room_type=second), person(room_type=first)).score == expected


def test_room_type_unavailable_when_missing() -> None:
    assert score_room(person(room_type=RoomType.PRIVATE_ROOM), person()).score is None


# --- Food ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        (FoodPreference.VEGETARIAN, FoodPreference.VEGETARIAN, 100),
        (FoodPreference.VEGAN, FoodPreference.VEGAN, 100),
        (FoodPreference.NON_VEGETARIAN, FoodPreference.NON_VEGETARIAN, 100),
        (FoodPreference.VEGETARIAN, FoodPreference.VEGAN, 70),
        (FoodPreference.VEGETARIAN, FoodPreference.NON_VEGETARIAN, 30),
        (FoodPreference.VEGAN, FoodPreference.NON_VEGETARIAN, 20),
    ],
)
def test_food(first: FoodPreference, second: FoodPreference, expected: int) -> None:
    assert (
        score_food(person(food_preference=first), person(food_preference=second)).score == expected
    )
    assert (
        score_food(person(food_preference=second), person(food_preference=first)).score == expected
    )


def test_food_unavailable_when_missing() -> None:
    assert score_food(person(), person(food_preference=FoodPreference.VEGAN)).score is None


# --- Combining the factors ------------------------------------------------------------


def test_combine_is_the_weighted_average() -> None:
    scores = {
        Factor.BUDGET: 100,
        Factor.SOCIETIES: 60,
        Factor.LIFESTYLE: 50,
        Factor.MOVE_IN: 100,
        Factor.ROOM: 0,
        Factor.FOOD: 100,
    }
    # (25x100 + 25x60 + 20x50 + 15x100 + 10x0 + 5x100) / 100 = 70
    assert combine(scores, DEFAULT_WEIGHTS) == 70


def test_unavailable_factors_are_left_out_and_the_rest_rescaled() -> None:
    scores = {
        Factor.BUDGET: 80,
        Factor.SOCIETIES: None,
        Factor.LIFESTYLE: None,
        Factor.MOVE_IN: 100,
        Factor.ROOM: None,
        Factor.FOOD: None,
    }
    # Only budget (25) and move-in (15) count: (25x80 + 15x100) / 40 = 87.5
    assert combine(scores, DEFAULT_WEIGHTS) == 88
    # Unavailable is not the same as zero:
    assert combine({**scores, Factor.SOCIETIES: 0}, DEFAULT_WEIGHTS) == 54


def test_nothing_to_compare_gives_no_score() -> None:
    result = calculate(person(), person())

    assert result.score is None
    assert set(result.unavailable) == set(Factor)
    assert result.summary == "Not enough information to calculate compatibility yet."


def test_custom_weights_are_used() -> None:
    scores = {factor: 0 for factor in Factor} | {Factor.FOOD: 100}
    only_food = {factor: 0 for factor in Factor} | {Factor.FOOD: 100}

    assert combine(scores, only_food) == 100
    assert combine(scores, DEFAULT_WEIGHTS) == 5


def test_no_shared_society_data_rescales_the_other_weights() -> None:
    # Nobody has a verified society yet: the society factor is unavailable
    # and its 25% is spread over the other five.
    a = replace(FULL, societies=())
    b = replace(FULL, societies=(choice("Unverified Heights", is_public=False),))

    result = calculate(a, b)
    societies = next(item for item in result.factors if item.factor == Factor.SOCIETIES)
    budget_result = next(item for item in result.factors if item.factor == Factor.BUDGET)

    assert result.score == 100
    assert result.unavailable == (Factor.SOCIETIES,)
    assert societies.effective_weight == 0
    assert budget_result.effective_weight == pytest.approx(33.3)
    assert sum(item.effective_weight for item in result.factors) == pytest.approx(100, abs=0.2)
    assert "Could not compare: societies." in result.summary


def test_a_real_mismatch_on_societies_lowers_the_score() -> None:
    elsewhere = replace(FULL, societies=(choice("Lancor Lumina", locality="Guduvanchery"),))

    result = calculate(FULL, elsewhere)

    assert result.score == 75  # every other factor perfect, societies 0 of 25%
    assert result.unavailable == ()
    assert "You are looking in different areas." in result.summary


# --- Whole results ----------------------------------------------------------------------


def test_the_summary_explains_strengths_societies_and_differences() -> None:
    other = replace(
        FULL,
        move_in_date=FULL.move_in_date + timedelta(days=100),  # type: ignore[operator]
        food_preference=None,
    )

    result = calculate(FULL, other)

    assert result.summary == (
        "Strong compatibility in budget, lifestyle and room type. "
        "You both prefer Lancor Abode Valley and VGN Tranquil. "
        "Main differences: move-in date. "
        "Could not compare: food."
    )
    many = replace(FULL, societies=(choice("A", 1), choice("B", 2), choice("C", 3)))
    assert "You share 3 preferred societies." in calculate(many, many).summary


def test_results_are_the_same_both_ways_round_and_every_time() -> None:
    other = CompatibilityInput(
        min_budget=10000,
        max_budget=15000,
        move_in_date=date(2027, 2, 1),
        room_type=RoomType.NO_PREFERENCE,
        food_preference=FoodPreference.VEGAN,
        sleep_schedule=SleepSchedule.FLEXIBLE,
        cleanliness=CleanlinessLevel.VERY_TIDY,
        societies=(choice("VGN Tranquil", 1), choice("Lancor Abode Valley", 3)),
    )

    first = calculate(FULL, other)

    assert calculate(other, FULL) == first
    assert calculate(FULL, other) == first
    assert first.score is not None and 0 <= first.score <= 100


def test_explanations_never_promise_anything() -> None:
    result = calculate(FULL, FULL)
    text = " ".join([result.summary, *(item.explanation for item in result.factors)]).lower()

    assert result.score == 100
    for word in ("guarantee", "perfect", "will get along", "best match"):
        assert word not in text


# --- Configuration --------------------------------------------------------------------------


def _settings(**values: object) -> Settings:
    return Settings(  # type: ignore[call-arg]
        postgres_password="x",  # noqa: S106 - test value
        secret_key="k" * 32,
        **values,
    )


def test_settings_default_to_the_prd_weights() -> None:
    weights = _settings().compatibility_weights

    assert {Factor(name): weight for name, weight in weights.items()} == DEFAULT_WEIGHTS


@pytest.mark.parametrize(
    "weights",
    [
        {"budget": 50, "societies": 50},  # factors missing
        {"budget": 30, "societies": 25, "lifestyle": 20, "move_in": 15, "room": 10, "food": 5},
        {"budget": -5, "societies": 35, "lifestyle": 20, "move_in": 15, "room": 30, "food": 5},
    ],
)
def test_settings_reject_bad_weights(weights: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        _settings(compatibility_weights=weights)
