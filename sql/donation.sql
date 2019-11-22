-- ORDER: 36
-- DELETE FROM payment
-- DELETE FROM donation

-- PREPARATION -----------------------------------------------------------------
-- I create a temporary table all_contributions that keeps all the logic of
-- translating payment_instrument to payment methods etc. It's 20MB for 50k
-- donations
CREATE TEMPORARY TABLE all_contributions AS
SELECT
-- First info about contribution
    c.id AS contribution_id,
    c.total_amount AS amount,
    c.currency AS original_currency,
    c.total_amount AS original_amount,
    c.receive_date,

    CASE WHEN c.payment_instrument_id = 1 THEN 'paypal'
    WHEN c.payment_instrument_id = 2 THEN 'card'
    WHEN c.payment_instrument_id = 5 THEN 'bank_transfer'
    WHEN c.payment_instrument_id in (6,7,8) THEN 'sepa'
    END as payment_method,
    CASE WHEN c.contribution_status_id = 1 THEN 'success'
    WHEN c.contribution_status_id = 4 THEN 'failed'
    WHEN c.contribution_status_id IN (3, 7) THEN 'cancelled'
    END as status,
-- Second info about recurring donation it belongs to
    c.contribution_recur_id,
    rc.start_date as recur_start_date,
    COALESCE(rc.cancel_date, rc.end_date) AS recur_end_date,
    COALESCE(rc.frequency_unit, 'one-off') as frequency_unit,
    COALESCE(rc.frequency_interval, 1) as frequency_interval,
-- Then the external_id/system pair we use in donation record
    CASE WHEN c.contribution_recur_id IS NULL THEN 'civicrm_contribution'
    ELSE 'civicrm_contribution_recur'
    END as external_system,
    COALESCE(rc.id, c.id) as external_id

FROM
    ${SOURCE}.civicrm_contribution c
    LEFT JOIN
    ${SOURCE}.civicrm_contribution_recur rc
    ON c.contribution_recur_id = rc.id
WHERE
    c.payment_instrument_id IN (1,2,5,6,7,8)
    AND c.contribution_status_id IN (1,3,4,7)
    ;

-- Some indexes to speed up following operations
CREATE INDEX all_contributions_status ON all_contributions (status);
CREATE INDEX all_contributions_c_id ON all_contributions (contribution_id);
CREATE INDEX all_contributions_rc_id ON all_contributions (contribution_recur_id);
CREATE INDEX all_contributions_external_ids ON all_contributions (external_id, external_system);

-- DONATIONS -----------------------------------------------------------------
-- Insert donations both one-off and recurring in one go
-- Use DISTINCT to get recurring donation just once
INSERT INTO donation (
        contact_action_id,
        amount, total_amount, original_amount, original_currency,
        started_at, ended_at, payment_method,
        frequency_unit, frequency_interval,
        payment_count, failure_count,
        external_id, external_system
        )
SELECT DISTINCT
    ca.id,
-- total_amount will be updated for recurring donations below
    ac.amount, 0, ac.original_amount, ac.original_currency,
-- start, end dates
    COALESCE(ac.recur_start_date, ac.receive_date),
    ac.recur_end_date,
    ac.payment_method,
-- frequencies
    ac.frequency_unit,
    ac.frequency_interval,
-- agg count - zero for now
    0, 0,
-- external references
    ac.external_id,
    ac.external_system
FROM all_contributions ac
    JOIN contact_action ca ON ca.external_id = ac.external_id AND ca.external_system = ac.external_system

-- BEGIN INCREMENTAL
-- exclude by contact_action references in donation table
WHERE ca.id NOT IN (SELECT contact_action_id FROM donation)
-- END INCREMENTAL
    ;



-- PAYMENTS -----------------------------------------------------------------
-- BEGIN INCREMENTAL
SET @last_receive_date  = (SELECT max(receive_date) FROM payment); 
-- END INCREMENTAL

INSERT INTO payment
    (donation_id, receive_date, status)
SELECT
    d.id, ac.receive_date, ac.status
FROM donation d
    JOIN
    all_contributions ac ON d.external_system = ac.external_system AND d.external_id = ac.external_id
-- BEGIN INCREMENTAL
WHERE ac.receive_date > @last_receive_date;
-- END INCREMENTAL
    ;

-- BEGIN INCREMENTAL
-- if we just inserted new payments, check if old payments did not change status
UPDATE payment p -- update statuses
    JOIN donation d ON p.donation_id = d.id
    JOIN all_contributions ac
    ON d.external_system = ac.external_system
    AND d.external_id = ac.external_id
    AND p.receive_date = ac.receive_date
SET p.status = ac.status
WHERE p.status != ac.status AND ac.receive_date <= @last_receive_date
    ;
-- END INCREMENTAL

-- AGGREGATIONS ------------------------------------------------------------
-- Now update donations to set all aggregates for success payments
UPDATE donation d
    JOIN
    (SELECT
        d.id,
        d.amount * count(p.id) as total_amount,
        count(p.id) as payment_count
    FROM donation d
        LEFT JOIN payment p ON p.donation_id = d.id AND p.status='success'

    GROUP BY d.id
        ) succ ON d.id = succ.id
SET
    d.total_amount = succ.total_amount,
    d.payment_count = succ.payment_count
    ;

-- Update donations with fialed_count
UPDATE donation d
    JOIN
    (SELECT
        d.id,
        count(p.id) as failed_count
    FROM donation d
        LEFT JOIN payment p ON p.donation_id = d.id AND p.status='failed'
    GROUP BY d.id
        ) fail ON d.id = fail.id
SET d.failure_count = fail.failed_count
    ;

-- CLEANUP -------------------------------------------------------------------
DROP TABLE all_contributions;
