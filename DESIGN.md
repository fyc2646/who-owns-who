# Design Document

## Overview

`tripsettle` computes the minimal set of transfers needed to settle shared expenses among friends. It uses a greedy algorithm to minimize the number of transactions while ensuring all balances are cleared.

## Algorithm

### Net Balance Computation

For each person `p` in the event:

```
net[p] = total_paid_by(p) - fair_share_owed_by(p)
```

Where:
- `total_paid_by(p)` = sum of all amounts `p` paid as a payer
- `fair_share_owed_by(p)` = sum of all shares `p` owes as a participant

A positive net balance means others owe them money; negative means they owe others.

### Minimal Cash Flow Algorithm

The algorithm uses a greedy approach to minimize the number of transfers:

1. **Separate creditors and debtors**:
   - Creditors: people with `net > tolerance` (default 0.01)
   - Debtors: people with `net < -tolerance`

2. **Match largest creditor with largest debtor**:
   - Sort creditors by balance (descending), then by name/ID for determinism
   - Sort debtors by balance (ascending, most negative first), then by name/ID
   - Match the first creditor with the first debtor

3. **Create transfer**:
   - Transfer amount = `min(creditor_balance, -debtor_balance)`
   - Round to 2 decimal places

4. **Update balances**:
   - `creditor_balance -= transfer_amount`
   - `debtor_balance += transfer_amount`
   - Round both to 2 decimal places

5. **Repeat** until no creditors or debtors remain

This algorithm produces a minimal set of transfers (at most `n-1` transfers for `n` people) and is deterministic due to stable sorting.

### Time Complexity

- Net balance computation: O(A × P) where A = activities, P = participants per activity
- Minimal transfers: O(T × log T) where T = number of people with non-zero balances
- Overall: O(A × P + T × log T)

## Rounding Policy

### Banker's Rounding

All monetary amounts use `Decimal` with banker's rounding (round half to even) to 2 decimal places:

```python
from decimal import Decimal, ROUND_HALF_EVEN
amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
```

Examples:
- `10.555` → `10.56`
- `10.545` → `10.54`
- `10.5` → `10.50`

### Remainder Distribution

Due to rounding, balances may not sum exactly to zero. Any remainder within tolerance (0.01) is distributed using a **least-absolute-balance-first** strategy:

1. Sort people by absolute balance (ascending), then by name/ID
2. Distribute remainder in 0.01 increments
3. Continue until remainder is zero

This ensures:
- Deterministic distribution
- Minimal impact on individual balances
- Zero-sum invariant maintained

### Validation

- All amounts must be non-negative
- Fixed shares must sum to activity amount (within 0.01 tolerance)
- Weighted shares are automatically normalized to sum to 1.0
- Multi-payer amounts must sum to activity amount (within 0.01 tolerance)

## Split Strategies

### EQUAL

Split expense equally among all participants:

```
share[p] = activity.amount / len(participants)
```

Rounded to 2 decimal places. Any rounding remainder distributed using least-absolute-balance-first.

### WEIGHTED

Split based on weights (automatically normalized):

```
normalized_weight[p] = weight[p] / sum(all_weights)
share[p] = activity.amount * normalized_weight[p]
```

If weights don't sum to 1.0 (within 0.01 tolerance), they are re-normalized. If sum is zero or negative, raises `ValidationError`.

### FIXED_SHARES

Use exact amounts specified:

```
share[p] = shares[p]
```

Shares must sum to activity amount (within 0.01 tolerance). All shares must be non-negative.

## Data Model

### Person

Immutable dataclass with:
- `id: UUID` - Unique identifier
- `name: str` - Person's name

Names can be duplicated; IDs ensure uniqueness.

### Activity

Mutable dataclass with:
- `id: UUID` - Unique identifier
- `description: str` - Activity description
- `amount: Decimal` - Total amount
- `payer: Union[Person, List[tuple[Person, Decimal]]]` - Single payer or list of (payer, amount) tuples
- `participants: List[Person]` - People who participated
- `split_strategy: SplitStrategy` - How to split the expense
- `weights: Optional[Dict[Person, Decimal]]` - For WEIGHTED strategy
- `shares: Optional[Dict[Person, Decimal]]` - For FIXED_SHARES strategy
- `currency: str` - Currency code (default "USD")

### Event

Container for:
- `id: UUID` - Unique identifier
- `name: str` - Event name
- `people: List[Person]` - People in the event
- `activities: List[Activity]` - Expense activities
- `currency: str` - Currency code (default "USD")

### SettlementTransfer

Immutable dataclass with:
- `from_person: Person` - Person who owes money
- `to_person: Person` - Person who should receive money
- `amount: Decimal` - Transfer amount (rounded to 2 decimals)

## Serialization

### JSON Schema

Stable JSON schema for `Event`:

```json
{
  "id": "uuid-string",
  "name": "Event Name",
  "currency": "USD",
  "people": [
    {"id": "uuid-string", "name": "Person Name"}
  ],
  "activities": [
    {
      "id": "uuid-string",
      "description": "Activity Description",
      "amount": "100.00",
      "payer": {"id": "uuid-string", "name": "Person Name"},
      "participants": [...],
      "split_strategy": "EQUAL",
      "weights": {...},  // optional
      "shares": {...},   // optional
      "currency": "USD"
    }
  ]
}
```

### CSV Schema

**people.csv**:
```csv
id,name
uuid-1,Alice
uuid-2,Bob
```

**activities.csv**:
```csv
id,description,amount,payer_id,participants,split_strategy,weights,shares
uuid-1,Dinner,100.00,uuid-1,"uuid-1,uuid-2",EQUAL,,
```

## Error Handling

Custom exceptions in `tripsettle.errors`:

- `TripsettleError`: Base exception
- `ValidationError`: Invalid input (negative amounts, missing participants, etc.)
- `RoundingError`: Rounding operations failed or totals don't sum
- `StrategyError`: Invalid split strategy configuration

## Limitations

### Current (v0.1.0)

1. **Single Currency**: All activities must use the same currency as the event
2. **No Currency Conversion**: No support for multi-currency events
3. **No Partial Payments**: Can't mark transfers as "paid" or track payment status
4. **No Activity Groups**: Can't group activities or compute settlements per group
5. **No Recurring Activities**: Each activity must be added individually

### Future Enhancements

1. **Multi-Currency Support**: Per-activity currency with conversion
2. **Payment Tracking**: Mark transfers as paid, track payment history
3. **Activity Groups**: Group activities and compute per-group settlements
4. **Recurring Activities**: Support for repeating expenses
5. **Graph Visualization**: Export transfer graph for visualization
6. **Optimization Options**: Alternative algorithms (e.g., minimize total transfer amount)

## Testing Strategy

### Unit Tests

- Models: validation, serialization, edge cases
- Strategies: all split strategies, edge cases
- Compute: net balance, minimal transfers, rounding
- Utils: rounding, validation, remainder distribution

### Integration Tests

- Full workflow from event creation to settlement
- Example scenarios from requirements
- Edge cases: single person, person not in activity, etc.

### Coverage Goals

- 100% branch coverage for `compute.py` and `strategies.py`
- ≥95% overall coverage
- All error paths tested

## Performance Considerations

- Uses `Decimal` for precise money math (no floating-point errors)
- Deterministic sorting ensures reproducible results
- Greedy algorithm is efficient for typical use cases (< 100 people)
- For very large events (> 1000 people), consider optimizing the sorting step

## Security Considerations

- No network I/O or external API calls
- All input validated before processing
- UUIDs prevent ID collisions
- No code execution from serialized data

