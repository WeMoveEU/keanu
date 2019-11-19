-- ORDER: 36
-- DELETE FROM payment
-- DELETE FROM donation

-- One-off donations
BEGIN;
-- BEGIN INCREMENTAL
SET @last_donation_id = (SELECT max(id) FROM donation);
-- END INCREMENTAL

  INSERT INTO donation (
      amount, original_currency, original_amount, frequency_unit,
      started_at, payment_method, contact_action_id,
      total_amount, payment_count, failure_count,
      external_id, external_system
    )

    SELECT
      c.total_amount,
      c.currency as original_currency,
      c.total_amount as original_amount,
      'one-off',
      c.receive_date,
      CASE WHEN payment_instrument_id = 1 THEN 'paypal'
           WHEN payment_instrument_id = 2 THEN 'card'
           WHEN payment_instrument_id = 5 THEN 'bank_transfer'
           WHEN payment_instrument_id = 8 THEN 'sepa'
      END,
      ca.id as contact_action_id,
      0,
      0,
      0,
      c.id,
      'civicrm_contribution'

  FROM ${SOURCE}.civicrm_contribution c
    JOIN contact_action ca ON c.id = ca.external_id AND ca.external_system='civicrm_contribution'

    WHERE NOT c.is_test AND c.contribution_recur_id IS NULL
      AND c.payment_instrument_id IN (1, 2, 5, 8)
  -- BEGIN INCREMENTAL
      AND c.id NOT IN (SELECT external_id FROM donation where external_system = 'civicrm_contribution')
  -- END INCREMENTAL

  ;

  INSERT INTO payment
    (donation_id, receive_date, status)

    SELECT
      d.id,
      c.receive_date,
      CASE WHEN c.contribution_status_id = 1 THEN 'success'
           WHEN c.contribution_status_id = 3 THEN 'failed'
           WHEN c.contribution_status_id IN (4, 7) THEN 'cancelled'
      END

    FROM ${SOURCE}.civicrm_contribution c
    JOIN donation d ON d.external_id=c.id AND d.external_system='civicrm_contribution'

    WHERE NOT c.is_test AND c.contribution_recur_id IS NULL
      AND c.payment_instrument_id IN (1, 2, 6, 7)
      AND c.contribution_status_id IN (1, 3, 4, 7)
-- BEGIN INCREMENTAL
AND d.id > @last_donation_id AND d.id <= LAST_INSERT_ID()
-- END INCREMENTAL
  ;
COMMIT;

-- Recurring donations
BEGIN;
-- BEGIN INCREMENTAL
SET @last_donation_id = (SELECT max(id) FROM donation);
-- END INCREMENTAL

  INSERT INTO donation (
      amount, original_currency, original_amount, frequency_unit, frequency_interval,
      started_at, payment_method, contact_action_id, ended_at,
      total_amount, payment_count, failure_count,
      external_id, external_system
    )

    SELECT
      rd.amount,
      rd.currency as original_currency,
      rd.amount as original_amount,
      rd.frequency_unit,
      rd.frequency_interval,
      rd.start_date,
      CASE WHEN payment_instrument_id = 1 THEN 'paypal'
           WHEN payment_instrument_id = 2 THEN 'card'
           WHEN payment_instrument_id in (6,7) THEN 'sepa'
      END,
      ca.id as contact_action_id,
      COALESCE(rd.cancel_date, rd.end_date) AS end_date,
      0,
      0,
      rd.failure_count,
      rd.id,
      'civicrm_contribution_recur'

    FROM ${SOURCE}.civicrm_contribution_recur rd
    JOIN contact_action ca ON rd.id = ca.external_id AND ca.external_system='civicrm_contribution_recur'

    WHERE NOT rd.is_test
      AND rd.payment_instrument_id in (1, 2, 6, 7)
      AND rd.frequency_unit = 'month'
  -- BEGIN INCREMENTAL
      AND rd.id NOT IN (SELECT external_id FROM donation where external_system = 'civicrm_contribution_recur')
  -- END INCREMENTAL

    GROUP BY contact_action_id, rd.id
  ;

  INSERT INTO payment
    (donation_id, receive_date, status)

    SELECT
      d.id,
      c.receive_date,
      CASE WHEN c.contribution_status_id = 1 THEN 'success'
           WHEN c.contribution_status_id = 3 THEN 'failed'
           WHEN c.contribution_status_id IN (4, 7) THEN 'cancelled'
      END

    FROM ${SOURCE}.civicrm_contribution c
    JOIN ${SOURCE}.civicrm_contribution_recur rd ON rd.id = c.contribution_recur_id
    JOIN donation d ON d.external_id=rd.id AND d.external_system='civicrm_contribution_recur'

    WHERE NOT rd.is_test AND NOT c.is_test
      AND c.contribution_status_id IN (1, 3, 4, 7)
      AND rd.payment_instrument_id in (1, 2, 6, 7)
      AND rd.frequency_unit = 'month'
  -- BEGIN INCREMENTAL
      AND d.id > @last_donation_id AND d.id <= LAST_INSERT_ID()
  -- END INCREMENTAL

  ;
COMMIT;
