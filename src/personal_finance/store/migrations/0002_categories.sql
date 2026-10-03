-- Categories assigned by local rules. NULL means no rule matched. Re-running
-- categorization recomputes every value, so rule changes apply retroactively.

ALTER TABLE transactions ADD COLUMN category text;

-- Monthly totals per category and currency, excluding transfers. Card activity
-- counts in its billing month, as in monthly_flows.
CREATE VIEW monthly_categories AS
SELECT
    t.currency,
    date_trunc(
        'month', CASE WHEN a.kind = 'credit_card' THEN s.period_end ELSE t.occurred_on END
    )::date AS month,
    coalesce(t.category, 'uncategorized') AS category,
    sum(t.amount) FILTER (WHERE t.amount > 0) AS income,
    sum(t.amount) FILTER (WHERE t.amount < 0) AS spending,
    count(*) AS transactions
FROM transactions t
JOIN accounts a ON a.id = t.account_id
JOIN statements s ON s.id = t.statement_id
WHERE NOT t.is_transfer
GROUP BY t.currency, month, coalesce(t.category, 'uncategorized');
