# Transaction Cases

These guidelines describe how card transactions discovered from bank notification emails are recorded. Public documentation stays generic: specific financial institutions and card products are not named (see [DATA_POLICY.md](DATA_POLICY.md)).

## Card identification

Cards are identified by their last four digits only. Full card numbers must not be stored. Fixtures use invented last-four digits.

## Card types

- Debit card
- Credit card

## Transaction cases

| Card type | Case | Record handling |
| --- | --- | --- |
| Debit | Debit-card purchase | Record the transaction. |
| Credit | Credit-card charge | Record the transaction. |
| Credit | Credit-card charge followed by a reversal | Record both the original charge and the reversal as separate transactions. |

## Reversals

Credit-card reversals are retained as transactions. They do not delete or overwrite the original charge. Debit-card reversals are not yet documented.
