-- One statement per account, period end, and profile. Some institutions send
-- each currency of a card as its own document with its own profile; a second
-- copy of the same document is still rejected, and overlapping periods in one
-- currency still show up as continuity breaks.

ALTER TABLE statements DROP CONSTRAINT statements_account_id_period_end_key;
ALTER TABLE statements ADD CONSTRAINT statements_account_period_profile_key
    UNIQUE (account_id, period_end, profile);
