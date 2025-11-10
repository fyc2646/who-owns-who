"""Split strategy implementations for computing fair shares."""

from decimal import Decimal
from typing import Dict, List

from tripsettle.errors import StrategyError
from tripsettle.models import Activity, Person, SplitStrategy
from tripsettle.utils import round_money


def compute_equal_share(activity: Activity, participant: Person) -> Decimal:
    """
    Compute participant's share for EQUAL split strategy.

    Parameters
    ----------
    activity : Activity
        The activity.
    participant : Person
        The participant.

    Returns
    -------
    Decimal
        The participant's share.

    Raises
    ------
    StrategyError
        If participant is not in the activity.
    """
    if participant not in activity.participants:
        raise StrategyError(f"Participant {participant.name} is not in activity {activity.description}")

    num_participants = len(activity.participants)
    if num_participants == 0:
        return Decimal("0")

    share = activity.amount / Decimal(num_participants)
    return round_money(share)


def compute_weighted_share(activity: Activity, participant: Person) -> Decimal:
    """
    Compute participant's share for WEIGHTED split strategy.

    Parameters
    ----------
    activity : Activity
        The activity.
    participant : Person
        The participant.

    Returns
    -------
    Decimal
        The participant's share.

    Raises
    ------
    StrategyError
        If weights are missing or participant is not in weights.
    """
    if not activity.weights:
        raise StrategyError(f"WEIGHTED strategy requires weights for activity {activity.description}")

    if participant not in activity.weights:
        raise StrategyError(f"Participant {participant.name} not found in weights for activity {activity.description}")

    weight = activity.weights[participant]
    share = activity.amount * weight
    return round_money(share)


def compute_fixed_share(activity: Activity, participant: Person) -> Decimal:
    """
    Compute participant's share for FIXED_SHARES split strategy.

    Parameters
    ----------
    activity : Activity
        The activity.
    participant : Person
        The participant.

    Returns
    -------
    Decimal
        The participant's share.

    Raises
    ------
    StrategyError
        If shares are missing or participant is not in shares.
    """
    if not activity.shares:
        raise StrategyError(f"FIXED_SHARES strategy requires shares for activity {activity.description}")

    if participant not in activity.shares:
        raise StrategyError(f"Participant {participant.name} not found in shares for activity {activity.description}")

    share = activity.shares[participant]
    return round_money(share)


def compute_participant_share(activity: Activity, participant: Person) -> Decimal:
    """
    Compute a participant's fair share for an activity based on split strategy.

    Parameters
    ----------
    activity : Activity
        The activity.
    participant : Person
        The participant.

    Returns
    -------
    Decimal
        The participant's share.
    """
    if activity.split_strategy == SplitStrategy.EQUAL:
        return compute_equal_share(activity, participant)
    elif activity.split_strategy == SplitStrategy.WEIGHTED:
        return compute_weighted_share(activity, participant)
    elif activity.split_strategy == SplitStrategy.FIXED_SHARES:
        return compute_fixed_share(activity, participant)
    else:
        raise StrategyError(f"Unknown split strategy: {activity.split_strategy}")


def compute_all_shares(activity: Activity) -> Dict[Person, Decimal]:
    """
    Compute fair shares for all participants in an activity.

    Parameters
    ----------
    activity : Activity
        The activity.

    Returns
    -------
    Dict[Person, Decimal]
        Mapping of participant to their fair share.
    """
    shares = {}
    for participant in activity.participants:
        shares[participant] = compute_participant_share(activity, participant)
    return shares

