"""Compatibility scoring: how well two students' stated preferences fit.

This module is pure Python. It reads nothing from the database and has no
side effects, so the same two inputs always give the same result, and every
rule can be unit-tested on its own.

How the score is built (PRD section 8.6):

1. Six factors are each scored from 0 to 100 by their own function below:
   budget, societies, lifestyle, move-in date, room type and food.
2. A factor that cannot be judged (for example, one person never answered)
   is marked unavailable. It is NOT treated as a mismatch and NOT as a
   match: it is left out.
3. The overall score is the weighted average of the factors that could be
   judged, using the configured weights (default 25/25/20/15/10/5),
   rounded to a whole number. Leaving a factor out therefore spreads its
   weight over the others in proportion.

Only societies that students can currently see (verified and active, in a
verified and active locality) are ever compared. A retired, switched-off
or unverified society can never raise a score.

The score is a decision aid. It is never a promise that two people will
get on, and the wording here never claims otherwise.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.models.enums import (
    CleanlinessLevel,
    FoodPreference,
    GuestFrequency,
    HabitFrequency,
    RoomType,
    SleepSchedule,
    SocialPreference,
)


class Factor(StrEnum):
    BUDGET = "budget"
    SOCIETIES = "societies"
    LIFESTYLE = "lifestyle"
    MOVE_IN = "move_in"
    ROOM = "room"
    FOOD = "food"


FACTOR_LABELS: Mapping[Factor, str] = {
    Factor.BUDGET: "Budget",
    Factor.SOCIETIES: "Societies",
    Factor.LIFESTYLE: "Lifestyle",
    Factor.MOVE_IN: "Move-in date",
    Factor.ROOM: "Room type",
    Factor.FOOD: "Food",
}

# Used only when no weights are passed in. The running app passes the
# validated weights from settings (COMPATIBILITY_WEIGHTS).
DEFAULT_WEIGHTS: Mapping[Factor, int] = {
    Factor.BUDGET: 25,
    Factor.SOCIETIES: 25,
    Factor.LIFESTYLE: 20,
    Factor.MOVE_IN: 15,
    Factor.ROOM: 10,
    Factor.FOOD: 5,
}

# A factor scoring at least this is called a strength; below WEAK, a difference.
STRONG = 75
WEAK = 40


class AreaOverlap(StrEnum):
    """Whether two people want to live in the same place. Discovery uses
    this to show people who share your societies first (PRD section 1)."""

    SAME_SOCIETY = "SAME_SOCIETY"
    SAME_LOCALITY = "SAME_LOCALITY"
    NONE = "NONE"
    # One of them has no society that can be compared.
    UNKNOWN = "UNKNOWN"


# --- Inputs -----------------------------------------------------------------


@dataclass(frozen=True)
class SocietyChoice:
    society_id: uuid.UUID
    society_name: str
    locality_id: uuid.UUID
    locality_name: str
    # 1 is the person's first choice.
    priority: int
    # True only while students can see the society AND its locality. Choices
    # that are not public are ignored, whatever the caller passes in.
    is_public: bool


@dataclass(frozen=True)
class CompatibilityInput:
    """One person's answers. Every field may be missing (None)."""

    min_budget: int | None = None
    max_budget: int | None = None
    move_in_date: date | None = None
    room_type: RoomType | None = None
    food_preference: FoodPreference | None = None
    smoking: HabitFrequency | None = None
    drinking: HabitFrequency | None = None
    sleep_schedule: SleepSchedule | None = None
    cleanliness: CleanlinessLevel | None = None
    social: SocialPreference | None = None
    guests: GuestFrequency | None = None
    societies: tuple[SocietyChoice, ...] = ()

    def public_societies(self) -> list[SocietyChoice]:
        """The choices that count, most preferred first."""
        return sorted(
            (choice for choice in self.societies if choice.is_public),
            key=lambda choice: (choice.priority, choice.society_name),
        )


# --- Outputs ----------------------------------------------------------------


@dataclass(frozen=True)
class Scored:
    """What one factor function returns: a score (None if it could not be
    judged) and one sentence saying why."""

    score: int | None
    explanation: str


@dataclass(frozen=True)
class FactorResult:
    factor: Factor
    label: str
    # 0 to 100, or None when the factor could not be judged.
    score: int | None
    explanation: str
    # The configured weight, in percent.
    weight: int
    # The share of the final score this factor actually had, after
    # unavailable factors were left out. 0 for an unavailable factor.
    effective_weight: float

    @property
    def available(self) -> bool:
        return self.score is not None


@dataclass(frozen=True)
class CompatibilityResult:
    # 0 to 100, or None if not a single factor could be judged.
    score: int | None
    factors: tuple[FactorResult, ...]
    summary: str
    area_overlap: AreaOverlap
    shared_societies: tuple[str, ...]

    @property
    def unavailable(self) -> tuple[Factor, ...]:
        return tuple(result.factor for result in self.factors if not result.available)


# --- Small helpers ------------------------------------------------------------


def round_half_up(value: float) -> int:
    """Round .5 up, every time. (Python's round() sends 0.5 to the even
    number, which would surprise anyone checking a score by hand.)"""
    return math.floor(value + 0.5)


def format_inr(amount: int) -> str:
    """₹12,000 or ₹1,00,000: Indian digit grouping, as people write it."""
    digits = str(abs(amount))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join([*groups, tail])
    return f"₹{digits}"


def _join(items: Sequence[str]) -> str:
    """ "a", "a and b", "a, b and c"."""
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


# --- Factor 1: budget ---------------------------------------------------------

# Two budgets that do not overlap score less the further apart they are,
# reaching 0 when the gap is 30% of the lower budget's maximum.
_BUDGET_GAP_LIMIT = 0.30


def score_budget(a: CompatibilityInput, b: CompatibilityInput) -> Scored:
    """Overlapping ranges score 70 to 100; separate ranges 0 to 60.

    Budgets are compared as ranges, not exact amounts (PRD 8.6). When they
    overlap, the score grows with how much of the narrower range is shared.
    """
    values = (a.min_budget, a.max_budget, b.min_budget, b.max_budget)
    if any(value is None for value in values):
        return Scored(None, "Not enough information to compare budgets.")
    a_min, a_max, b_min, b_max = (int(value) for value in values)  # type: ignore[arg-type]

    low, high = max(a_min, b_min), min(a_max, b_max)
    if high >= low:
        narrower = min(a_max - a_min, b_max - b_min)
        shared = 1.0 if narrower == 0 else (high - low) / narrower
        score = round_half_up(70 + 30 * shared)
        if high == low:
            return Scored(score, f"Your budgets meet at {format_inr(low)} a month.")
        return Scored(
            score,
            f"Your budgets overlap between {format_inr(low)} and {format_inr(high)} a month.",
        )

    gap = low - high
    relative_gap = gap / high if high > 0 else 1.0
    score = max(0, round_half_up(60 * (1 - relative_gap / _BUDGET_GAP_LIMIT)))
    return Scored(score, f"Your budgets do not overlap: they are {format_inr(gap)} apart.")


# --- Factor 2: societies --------------------------------------------------------


def _rank_score(rank_a: int, rank_b: int) -> int:
    """Both ranking a society first scores 100. Each place lower, for either
    person, costs 10 points, down to a floor of 60."""
    return max(60, 100 - 10 * (rank_a - 1) - 10 * (rank_b - 1))


def score_societies(
    a: CompatibilityInput, b: CompatibilityInput
) -> tuple[Scored, AreaOverlap, tuple[str, ...]]:
    """Shared societies score 60 to 100 (higher when both rank them high),
    a shared locality with different societies 40, nothing in common 0.

    Ranks are counted among each person's public choices only, so if
    someone's first choice was retired, their second becomes their first.
    """
    a_choices, b_choices = a.public_societies(), b.public_societies()
    if not a_choices or not b_choices:
        return (
            Scored(None, "Not enough verified societies to compare."),
            AreaOverlap.UNKNOWN,
            (),
        )

    a_rank = {choice.society_id: rank for rank, choice in enumerate(a_choices, start=1)}
    b_rank = {choice.society_id: rank for rank, choice in enumerate(b_choices, start=1)}
    shared = [choice for choice in a_choices if choice.society_id in b_rank]

    if shared:
        ranked = sorted(
            shared,
            key=lambda choice: (
                -_rank_score(a_rank[choice.society_id], b_rank[choice.society_id]),
                choice.society_name,
            ),
        )
        best = ranked[0]
        score = _rank_score(a_rank[best.society_id], b_rank[best.society_id])
        names = tuple(choice.society_name for choice in ranked)
        if len(names) == 1:
            if a_rank[best.society_id] == b_rank[best.society_id] == 1:
                explanation = f"You both chose {best.society_name} as your first choice."
            else:
                explanation = f"You both chose {best.society_name}."
        else:
            explanation = f"You both chose {_join(list(names))}."
        return Scored(score, explanation), AreaOverlap.SAME_SOCIETY, names

    b_localities = {choice.locality_id for choice in b_choices}
    shared_areas = sorted(
        {choice.locality_name for choice in a_choices if choice.locality_id in b_localities}
    )
    if shared_areas:
        return (
            Scored(
                40,
                f"You both want to live in {_join(shared_areas)}, "
                "but chose different societies there.",
            ),
            AreaOverlap.SAME_LOCALITY,
            (),
        )
    return (
        Scored(0, "You chose different societies in different areas."),
        AreaOverlap.NONE,
        (),
    )


# --- Factor 3: lifestyle ----------------------------------------------------------

_ORDINAL_SIMILARITY = {0: 100, 1: 50, 2: 0}


def _ordinal(value_a: StrEnum, value_b: StrEnum, scale: Sequence[StrEnum]) -> int:
    return _ORDINAL_SIMILARITY[abs(scale.index(value_a) - scale.index(value_b))]


def _sleep(value_a: SleepSchedule, value_b: SleepSchedule) -> int:
    if value_a == value_b:
        return 100
    if SleepSchedule.FLEXIBLE in (value_a, value_b):
        return 75
    return 0  # an early bird and a night owl


@dataclass(frozen=True)
class _Habit:
    name: str  # how a difference is described
    attribute: str
    # How a shared answer is described, e.g. "early riser".
    shared: Mapping[StrEnum, str]
    scale: tuple[StrEnum, ...] = ()


_HABITS: tuple[_Habit, ...] = (
    _Habit(
        "sleep schedule",
        "sleep_schedule",
        {
            SleepSchedule.EARLY_BIRD: "early riser",
            SleepSchedule.NIGHT_OWL: "night owl",
            SleepSchedule.FLEXIBLE: "flexible sleeper",
        },
    ),
    _Habit(
        "tidiness",
        "cleanliness",
        {
            CleanlinessLevel.RELAXED: "relaxed about mess",
            CleanlinessLevel.TIDY: "tidy",
            CleanlinessLevel.VERY_TIDY: "very tidy",
        },
        (CleanlinessLevel.RELAXED, CleanlinessLevel.TIDY, CleanlinessLevel.VERY_TIDY),
    ),
    _Habit(
        "how social a home you want",
        "social",
        {
            SocialPreference.QUIET: "prefers a quiet home",
            SocialPreference.BALANCED: "balanced social life",
            SocialPreference.SOCIAL: "enjoys a social home",
        },
        (SocialPreference.QUIET, SocialPreference.BALANCED, SocialPreference.SOCIAL),
    ),
    _Habit(
        "guests",
        "guests",
        {
            GuestFrequency.RARELY: "rarely has guests",
            GuestFrequency.SOMETIMES: "sometimes has guests",
            GuestFrequency.OFTEN: "often has guests",
        },
        (GuestFrequency.RARELY, GuestFrequency.SOMETIMES, GuestFrequency.OFTEN),
    ),
    _Habit(
        "smoking",
        "smoking",
        {
            HabitFrequency.NEVER: "non-smoker",
            HabitFrequency.OCCASIONALLY: "smokes occasionally",
            HabitFrequency.REGULARLY: "smokes regularly",
        },
        (HabitFrequency.NEVER, HabitFrequency.OCCASIONALLY, HabitFrequency.REGULARLY),
    ),
    _Habit(
        "drinking",
        "drinking",
        {
            HabitFrequency.NEVER: "doesn't drink",
            HabitFrequency.OCCASIONALLY: "drinks occasionally",
            HabitFrequency.REGULARLY: "drinks regularly",
        },
        (HabitFrequency.NEVER, HabitFrequency.OCCASIONALLY, HabitFrequency.REGULARLY),
    ),
)


def score_lifestyle(a: CompatibilityInput, b: CompatibilityInput) -> Scored:
    """The average similarity of the habits BOTH people answered.

    Sleep: same 100, one flexible 75, early bird with night owl 0.
    The rest are three-step scales: same 100, one step apart 50, opposite 0.
    Habits only one person answered are skipped, not guessed.
    """
    scores: list[int] = []
    shared: list[str] = []
    differences: list[str] = []
    for habit in _HABITS:
        value_a, value_b = getattr(a, habit.attribute), getattr(b, habit.attribute)
        if value_a is None or value_b is None:
            continue
        similarity = (
            _sleep(value_a, value_b) if not habit.scale else _ordinal(value_a, value_b, habit.scale)
        )
        scores.append(similarity)
        if similarity == 100:
            shared.append(habit.shared[value_a])
        elif similarity == 0:
            differences.append(habit.name)

    if not scores:
        return Scored(None, "Not enough lifestyle answers to compare.")

    parts: list[str] = []
    if shared:
        parts.append(f"In common: {_join(shared)}.")
    if differences:
        parts.append(f"Different {_join(differences)}.")
    if not parts:
        parts.append("Your habits are similar but not the same.")
    if len(scores) < len(_HABITS):
        parts.append(f"Based on {len(scores)} of {len(_HABITS)} habits.")
    return Scored(round_half_up(sum(scores) / len(scores)), " ".join(parts))


# --- Factor 4: move-in date ---------------------------------------------------------

# (most days apart, score), checked in order.
_MOVE_IN_STEPS: tuple[tuple[int, int], ...] = (
    (7, 100),
    (14, 85),
    (30, 70),
    (60, 40),
    (90, 20),
)


def score_move_in(a: CompatibilityInput, b: CompatibilityInput) -> Scored:
    """Within a week 100, two weeks 85, a month 70, two months 40, three
    months 20, further apart 0."""
    if a.move_in_date is None or b.move_in_date is None:
        return Scored(None, "Not enough information to compare move-in dates.")
    days = abs((a.move_in_date - b.move_in_date).days)
    score = next((points for limit, points in _MOVE_IN_STEPS if days <= limit), 0)
    if days == 0:
        return Scored(score, "You want to move in on the same date.")
    unit = "day" if days == 1 else "days"
    return Scored(score, f"Your move-in dates are {days} {unit} apart.")


# --- Factor 5: room type ----------------------------------------------------------

_ROOM_WORDS = {
    RoomType.PRIVATE_ROOM: "a private room",
    RoomType.SHARED_ROOM: "a shared room",
}


def score_room(a: CompatibilityInput, b: CompatibilityInput) -> Scored:
    """Same answer 100, one person without a preference 80, private against
    shared 30."""
    if a.room_type is None or b.room_type is None:
        return Scored(None, "Not enough information to compare room types.")
    if a.room_type == b.room_type:
        if a.room_type == RoomType.NO_PREFERENCE:
            return Scored(100, "Neither of you minds which type of room.")
        return Scored(100, f"You both want {_ROOM_WORDS[a.room_type]}.")
    if RoomType.NO_PREFERENCE in (a.room_type, b.room_type):
        return Scored(80, "One of you has no room preference, so this can work either way.")
    return Scored(30, "One of you wants a private room and the other a shared room.")


# --- Factor 6: food -------------------------------------------------------------------

_FOOD_WORDS = {
    FoodPreference.VEGETARIAN: "vegetarian",
    FoodPreference.VEGAN: "vegan",
    FoodPreference.NON_VEGETARIAN: "non-vegetarian",
}
_FOOD_PAIRS: Mapping[frozenset[FoodPreference], int] = {
    frozenset({FoodPreference.VEGETARIAN, FoodPreference.VEGAN}): 70,
    frozenset({FoodPreference.VEGETARIAN, FoodPreference.NON_VEGETARIAN}): 30,
    frozenset({FoodPreference.VEGAN, FoodPreference.NON_VEGETARIAN}): 20,
}


def score_food(a: CompatibilityInput, b: CompatibilityInput) -> Scored:
    """Same 100, vegetarian with vegan 70, vegetarian with non-vegetarian 30,
    vegan with non-vegetarian 20. (Many shared flats share a kitchen.)"""
    if a.food_preference is None or b.food_preference is None:
        return Scored(None, "Not enough information to compare food preferences.")
    if a.food_preference == b.food_preference:
        return Scored(100, f"You are both {_FOOD_WORDS[a.food_preference]}.")
    score = _FOOD_PAIRS[frozenset({a.food_preference, b.food_preference})]
    words = sorted(_FOOD_WORDS[value] for value in (a.food_preference, b.food_preference))
    return Scored(score, f"Different food preferences: {words[0]} and {words[1]}.")


# --- Putting it together ------------------------------------------------------------


def combine(scores: Mapping[Factor, int | None], weights: Mapping[Factor, int]) -> int | None:
    """The weighted average of the factors that could be judged.

    Unavailable factors are left out and the remaining weights are scaled
    up to fill their place. None if nothing at all could be judged.
    """
    judged = {factor: score for factor, score in scores.items() if score is not None}
    total_weight = sum(weights[factor] for factor in judged)
    if total_weight == 0:
        return None
    weighted = sum(weights[factor] * score for factor, score in judged.items())
    return round_half_up(weighted / total_weight)


def _summary(results: Sequence[FactorResult], area: AreaOverlap, shared: Sequence[str]) -> str:
    if all(not result.available for result in results):
        return "Not enough information to calculate compatibility yet."

    sentences: list[str] = []
    others = [result for result in results if result.factor != Factor.SOCIETIES]
    strengths = [
        result.label.lower()
        for result in others
        if result.score is not None and result.score >= STRONG
    ]
    if strengths:
        sentences.append(f"Strong compatibility in {_join(strengths)}.")

    if area == AreaOverlap.SAME_SOCIETY:
        if len(shared) <= 2:
            sentences.append(f"You both prefer {_join(list(shared))}.")
        else:
            sentences.append(f"You share {len(shared)} preferred societies.")
    elif area == AreaOverlap.SAME_LOCALITY:
        sentences.append("You prefer the same area but different societies.")
    elif area == AreaOverlap.NONE:
        sentences.append("You are looking in different areas.")

    differences = [
        result.label.lower()
        for result in others
        if result.score is not None and result.score < WEAK
    ]
    if differences:
        sentences.append(f"Main differences: {_join(differences)}.")

    unavailable = [result.label.lower() for result in results if not result.available]
    if unavailable:
        sentences.append(f"Could not compare: {_join(unavailable)}.")
    return " ".join(sentences)


def calculate(
    a: CompatibilityInput,
    b: CompatibilityInput,
    weights: Mapping[Factor, int] = DEFAULT_WEIGHTS,
) -> CompatibilityResult:
    """Score two people. The result is the same whichever way round they
    are passed, and the same every time for the same answers."""
    society_scored, area, shared = score_societies(a, b)
    scored: dict[Factor, Scored] = {
        Factor.BUDGET: score_budget(a, b),
        Factor.SOCIETIES: society_scored,
        Factor.LIFESTYLE: score_lifestyle(a, b),
        Factor.MOVE_IN: score_move_in(a, b),
        Factor.ROOM: score_room(a, b),
        Factor.FOOD: score_food(a, b),
    }
    available_weight = sum(
        weights[factor] for factor, result in scored.items() if result.score is not None
    )
    results = tuple(
        FactorResult(
            factor=factor,
            label=FACTOR_LABELS[factor],
            score=result.score,
            explanation=result.explanation,
            weight=weights[factor],
            effective_weight=(
                round(100 * weights[factor] / available_weight, 1)
                if result.score is not None and available_weight
                else 0.0
            ),
        )
        for factor, result in scored.items()
    )
    overall = combine({factor: result.score for factor, result in scored.items()}, weights)
    return CompatibilityResult(
        score=overall,
        factors=results,
        summary=_summary(results, area, shared),
        area_overlap=area,
        shared_societies=shared,
    )
