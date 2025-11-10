"""Settlement computation: net balance calculation and minimal cash flow algorithm."""

from decimal import Decimal
from typing import Dict, List, Tuple

from tripsettle.errors import RoundingError
from tripsettle.models import Activity, Event, Person, SettlementTransfer
from tripsettle.strategies import compute_all_shares
from tripsettle.utils import ensure_zero_sum, round_money


def compute_net_balances(event: Event) -> Dict[Person, Decimal]:
    """
    Compute net balance for each person in the event.

    Net balance = total_paid - fair_share_owed
    Positive => others owe them; negative => they owe others.

    Parameters
    ----------
    event : Event
        The event to compute balances for.

    Returns
    -------
    Dict[Person, Decimal]
        Mapping of person to their net balance.
    """
    balances: Dict[Person, Decimal] = {person: Decimal("0") for person in event.people}

    for activity in event.activities:
        # Compute what each participant owes
        shares = compute_all_shares(activity)

        # Subtract what each participant owes from their balance
        for participant, share in shares.items():
            balances[participant] -= share

        # Add what each payer paid to their balance
        for payer, amount in activity.get_payers():
            balances[payer] += amount

    # Round all balances
    balances = {person: round_money(balance) for person, balance in balances.items()}

    # Ensure zero sum (allow slightly larger tolerance for rounding accumulation)
    balances = ensure_zero_sum(balances, tolerance=Decimal("0.02"))

    return balances


def compute_minimal_transfers(balances: Dict[Person, Decimal], tolerance: Decimal = Decimal("0.02")) -> List[SettlementTransfer]:
    """
    Compute minimal set of transfers to clear all balances using greedy algorithm.

    Algorithm:
    1. Maintain creditors (net > 0) and debtors (net < 0)
    2. Match largest creditor with largest debtor
    3. Transfer = min(credit, -debt)
    4. Update balances and repeat until all within tolerance

    Parameters
    ----------
    balances : Dict[Person, Decimal]
        Net balances for each person.
    tolerance : Decimal, default=Decimal("0.01")
        Tolerance for considering balance cleared.

    Returns
    -------
    List[SettlementTransfer]
        List of transfers needed to clear all balances.
    """
    # Create working copy
    working_balances = balances.copy()
    transfers: List[SettlementTransfer] = []

    while True:
        # Separate creditors and debtors
        creditors = [(p, b) for p, b in working_balances.items() if b > tolerance]
        debtors = [(p, b) for p, b in working_balances.items() if b < -tolerance]

        # If no creditors or debtors, we're done
        if not creditors or not debtors:
            break

        # Sort: largest creditor first, largest debtor (most negative) first
        # Use deterministic tie-breaking: sort by person name, then ID
        creditors.sort(key=lambda x: (-x[1], x[0].name, str(x[0].id)))
        debtors.sort(key=lambda x: (x[1], x[0].name, str(x[0].id)))

        # Match largest creditor with largest debtor
        creditor_person, creditor_balance = creditors[0]
        debtor_person, debtor_balance = debtors[0]

        # Transfer amount is minimum of credit and debt
        transfer_amount = min(creditor_balance, -debtor_balance)
        transfer_amount = round_money(transfer_amount)

        # Create transfer
        transfers.append(
            SettlementTransfer(
                from_person=debtor_person,
                to_person=creditor_person,
                amount=transfer_amount,
            )
        )

        # Update balances
        working_balances[creditor_person] -= transfer_amount
        working_balances[debtor_person] += transfer_amount

        # Round to avoid floating point issues
        working_balances[creditor_person] = round_money(working_balances[creditor_person])
        working_balances[debtor_person] = round_money(working_balances[debtor_person])

    # Verify final balances are within tolerance
    for person, balance in working_balances.items():
        if abs(balance) > tolerance:
            raise RoundingError(f"Final balance for {person.name} is {balance}, exceeds tolerance {tolerance}")

    # Sort transfers deterministically for stable output
    transfers.sort(key=lambda t: (t.from_person.name, str(t.from_person.id), t.to_person.name, str(t.to_person.id)))

    return transfers


def compute_settlement_summary(
    event: Event, balances: Dict[Person, Decimal]
) -> Dict[Person, Dict[str, Decimal]]:
    """
    Compute settlement summary showing paid, owed, and net for each person.

    Parameters
    ----------
    event : Event
        The event.
    balances : Dict[Person, Decimal]
        Net balances for each person.

    Returns
    -------
    Dict[Person, Dict[str, Decimal]]
        Summary with 'paid', 'owed', and 'net' for each person.
    """
    # Compute total paid and total owed for each person
    paid: Dict[Person, Decimal] = {person: Decimal("0") for person in event.people}
    owed: Dict[Person, Decimal] = {person: Decimal("0") for person in event.people}

    for activity in event.activities:
        # Add to paid
        for payer, amount in activity.get_payers():
            paid[payer] += amount

        # Add to owed
        shares = compute_all_shares(activity)
        for participant, share in shares.items():
            owed[participant] += share

    # Round and build summary
    summary = {}
    for person in sorted(event.people, key=lambda x: (x.name, str(x.id))):
        summary[person] = {
            "paid": round_money(paid[person]),
            "owed": round_money(owed[person]),
            "net": balances[person],
        }

    return summary

