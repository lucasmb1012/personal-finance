# Transaction Cases

These guidelines describe how transactions discovered from bank notification emails and account statements are recorded. Public documentation stays generic: financial institutions are referred to by pseudonyms (Bank A, Bank B), card products are not named, and notification wording is described rather than quoted (see [DATA_POLICY.md](DATA_POLICY.md)).

## Sources

| Source | Status |
| --- | --- |
| Bank A notification emails | Surveyed on 2026-09-26 |
| Bank A account statements | Surveyed on 2026-09-26 |
| Bank B account statements | Surveyed on 2026-10-03 |
| Bank B notification emails and card statements | Pending |

## Payment instruments

- **Credit card:** identified by the card's last four digits. An operator may hold several credit cards at once, and card numbers change when a card is replaced.
- **Account (debit):** purchases and withdrawals charged to an account are identified by the **account's** last four digits, not the debit card's.

Full card or account numbers must not be stored. Fixtures use invented last-four digits.

## Bank A notification cases

Every transaction notification carries its data in a single sentence in the email body.

| Case | Instrument | Fields in the notification | Currencies observed |
| --- | --- | --- | --- |
| Credit-card purchase | Credit card | Amount, currency, card last four, merchant descriptor, local date and time | Local currency, US dollars |
| Account purchase | Account | Amount, currency, account last four, merchant descriptor, local date and time | Local currency |
| ATM withdrawal | Account | Amount, currency, account last four, local date and time | Local currency |

Several subject lines, used at different times, map to the same account-purchase sentence, and the surrounding email template has changed over time while the sentence has not. Parsing therefore relies on the body sentence; the subject only helps classify the message.

Other messages from the same sender (statements, loan notices, security notices) are not transaction notifications. Statements are a separate source.

## Field formats

- **Amounts:** local-currency amounts are whole units with `.` as the thousands separator. US-dollar amounts use `,` as the decimal separator and always carry two decimals. No US-dollar amount of 1,000 or more has been observed; the parser must still accept a thousands separator.
- **Foreign purchases:** purchases abroad and from foreign online merchants arrive converted to US dollars. The original currency and the exchange rate are not in the notification.
- **Date and time:** the body states a local date and time without an offset. The message's `Date` header carries the exact instant. The operator's time zone observes daylight saving time.
- **Merchant descriptor:** raw text from the card network, not a clean merchant name. It may be truncated and may end with a city and a two-letter country code.

## Reversals

Bank A does not send notifications for reversals. Reversals, installments, fees, and interest come only from account statements.

When a credit-card reversal is recorded, it is kept as a separate transaction and does not delete or overwrite the original charge. Debit reversals are not yet documented.

## Bank A account statements

Statements arrive monthly as PDF attachments from the same sender as the notifications. Every file is protected with a short numeric password derived from a personal identifier.

| Statement | Frequency | Use |
| --- | --- | --- |
| Checking account | Monthly | Every account movement, with balances |
| Credit card | Monthly, one per card | Purchases, installments, payments, fees, taxes |
| Credit line interest settlement | Monthly | Explains the interest and tax charged to the account |
| Consumer loan installment notice | Monthly | Explains the loan installment charged to the account |

The first two are sources of transactions. The other two explain charges that already appear on the checking account statement and are not parsed yet.

### Checking account statement

- A table with date, description, branch, document, debit, credit, and balance columns. Debits and credits are only distinguishable by their horizontal position.
- Dates have a day and month but no year. A statement period can cross a year boundary, so the year is inferred from the period end.
- The balance is stated only on the last row of each day, and the statement states opening and closing balances. Replaying the rows reproduced every stated balance in every statement of the full history, and each closing balance equals the next statement's opening balance.
- A period's stated start date is the previous period's end date, the date of the opening balance. Entries dated that day appear only on the earlier statement, so consecutive statements do not overlap.
- Descriptions are truncated. Transfers include the counterparty's name, which is personal data about third parties.

### Credit card statement

- One statement per card and billing period. A statement can list several cards, each with its own subtotal. A replaced card continues on a new number, and its first statement carries on from the old card's last amount due.
- Each statement states the previous billing period and the previous amount due, which chains consecutive statements of a card.
- No statement is issued for a period with nothing to bill. The next statement then names a previous period that no statement covers, with a previous amount due of zero.
- Entries are grouped into sections (payments, single-installment purchases, installment purchases, voluntary products, fees and taxes), each ending with a stated total. The amount due equals the previous amount due plus every section total; this held in all samples.
- **Installments:** each installment entry carries the original purchase date, the original amount, the total with interest, the installment number and count (for example, 3 of 6), the installment amount, and the interest rate.
- An informational section lists new installment purchases whose first installment is billed next period (installment 0 of n). These entries are not billed and are excluded from the totals. In one sample its stated total omitted an interest-bearing purchase, so that total is not checked.
- Fees and a stamp tax per installment purchase appear only on statements.
- **Foreign purchases:** when there is foreign activity, the same file contains a second part in US dollars. Each entry carries the amount in the original currency, the amount in US dollars, a city, and a two-letter country code. The original currency itself is not named.

### Full-history validation

Every checking account and credit card statement in the mailbox was parsed, about four years of history. Every statement passed its own reconciliation checks without profile changes, and consecutive statements chained as described above, with one exception: one card statement was never delivered by email. Its absence showed up because the next statement's previous amount due did not match the last statement received. Backfill must therefore detect gaps by chaining statements rather than assume that every period arrived, and a missing statement has to be obtained from the institution directly.

### Bank B account statements

Bank B sends checking and demand deposit account statements as password-protected PDF attachments; the password is derived from a personal identifier. Card statements do not arrive by email and must be obtained from the institution.

- **Issued by volume, not by month:** a new statement is issued after roughly one hundred entries, or at year end, so a period can last from a few days to a year. Periods still chain without gaps: each starts on the previous period's end date.
- **Layout:** the same column-table layout as Bank A, with a date that includes the year, a balance on every row, and two layout generations whose columns differ by a few points. Some pages are shifted slightly, so column boundaries need a margin.
- **Balances:** there are no opening and closing balance rows. A summary line states the opening balance, total debits, total credits, and closing balance.
- **Characters:** older files write the dashes in dates as a minus sign rather than a hyphen; the PDF adapter normalizes them.
- **Re-sent statements:** a statement can be sent again as a summary without entries for the same period. It fails reconciliation and is not loaded.
- **Several accounts:** one operator can hold several checking and demand deposit accounts over time, each identified by its number.

Every Bank B account statement in the mailbox reconciled, except the summary-only copy, and each account chained without breaks. Transfers between Bank A and Bank B accounts cancel out quarter by quarter where both sides have statements.

### Loading into the ledger

Every checking account and credit card statement was loaded into the local database on 2026-10-03. Loading confirmed these cases:

- **Several card accounts:** an operator can hold more than one card account at the same institution, each with its own statements and billing cycle. A replaced card continues the same account, so the profile maps the old number's last four digits to the new one.
- **Installment dates:** an installment entry carries the original purchase date, not the billing date. Grouping card activity by entry date would put every installment in the purchase month, so reports group it by the statement's billing period.
- **Foreign-currency debt moved to local currency:** when the US-dollar balance is not paid in dollars, it reappears as a local-currency charge. The dollar purchases already count as spending, so that charge is a transfer between the two currency parts.
- **Transfers on the checking account:** transfers to and from the operator's own accounts, investment contributions, card payments, credit line draws and repayments, and loan disbursements are transfers. Loan installments are currently counted as spending.
- **Continuity:** the checking account chained without breaks. The card statement that was never delivered by email shows up as a balance break; a card account that skipped periods with nothing to bill shows up as a gap with chained balances.

### Cross-document reconciliation

The card payment debited from the checking account equals the card statement's amount due, and the loan installment debited from the account equals the installment notice's total. These links let one document confirm another.

## Authenticity

Only messages whose `Authentication-Results` header reports `dmarc=pass` are accepted. SPF alone is not required: legitimate notifications have been observed with a failing SPF check but a passing DKIM signature and DMARC result.
