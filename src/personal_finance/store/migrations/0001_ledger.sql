-- Core ledger: accounts, statements, their balances, and transactions.
-- Amounts are numeric, never floating point. See personal_finance.ledger.models
-- for sign conventions.

CREATE TABLE accounts (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    institution text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('checking', 'demand_deposit', 'credit_card')),
    -- The last four digits of the account number, or a profile name; never a full number.
    reference text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (institution, kind, reference)
);

CREATE TABLE statements (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id bigint NOT NULL REFERENCES accounts (id),
    -- The source file's SHA-256 makes loading idempotent; its name aids tracing.
    source_sha256 text NOT NULL UNIQUE,
    source_name text NOT NULL,
    profile text NOT NULL,
    period_start date,
    period_end date NOT NULL,
    checks_passed integer NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (account_id, period_end),
    CHECK (period_start IS NULL OR period_start <= period_end)
);

CREATE TABLE statement_balances (
    statement_id bigint NOT NULL REFERENCES statements (id) ON DELETE CASCADE,
    currency char(3) NOT NULL,
    opening numeric(18, 2) NOT NULL,
    closing numeric(18, 2) NOT NULL,
    PRIMARY KEY (statement_id, currency)
);

CREATE TABLE transactions (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    statement_id bigint NOT NULL REFERENCES statements (id) ON DELETE CASCADE,
    account_id bigint NOT NULL REFERENCES accounts (id),
    line integer NOT NULL,
    occurred_on date NOT NULL,
    description text NOT NULL,
    amount numeric(18, 2) NOT NULL,
    currency char(3) NOT NULL,
    is_transfer boolean NOT NULL DEFAULT false,
    balance_after numeric(18, 2),
    installment smallint,
    installments smallint,
    details jsonb NOT NULL DEFAULT '{}',
    UNIQUE (statement_id, line)
);

CREATE INDEX transactions_account_date ON transactions (account_id, occurred_on);

-- Monthly income, spending, and transfers per account and currency. Card
-- activity counts in the month its statement period ends, when it is billed:
-- an installment carries the original purchase date, but it is paid later.
CREATE VIEW monthly_flows AS
SELECT
    a.institution,
    a.kind,
    a.reference,
    t.currency,
    m.month,
    sum(t.amount) FILTER (WHERE NOT t.is_transfer AND t.amount > 0) AS income,
    sum(t.amount) FILTER (WHERE NOT t.is_transfer AND t.amount < 0) AS spending,
    sum(t.amount) FILTER (WHERE t.is_transfer) AS transfers,
    sum(t.amount) AS net,
    count(*) AS transactions
FROM transactions t
JOIN accounts a ON a.id = t.account_id
JOIN statements s ON s.id = t.statement_id
CROSS JOIN LATERAL (
    SELECT date_trunc(
        'month', CASE WHEN a.kind = 'credit_card' THEN s.period_end ELSE t.occurred_on END
    )::date AS month
) m
GROUP BY a.institution, a.kind, a.reference, t.currency, m.month;
