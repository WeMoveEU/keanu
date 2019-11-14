-- ORDER: 36
-- DELETE FROM donation

INSERT INTO
donation (amount, original_currency, original_amount,
          provider, contact_action_id, regular)
SELECT
c.total_amount,
c.currency,
c.total_amount,
CASE WHEN c.payment_instrument_id = 1 THEN 'paypal'
     WHEN c.payment_instrument_id = 2 THEN 'stripe'
     WHEN c.payment_instrument_id = 5 THEN 'bank'
     WHEN c.payment_instrument_id = 8 THEN 'sepa'
     ELSE NULL
END as provider,
ca.id,
FALSE as regular

FROM
wemove_47.civicrm_contribution c
JOIN contact_action ca ON c.id = ca.external_id AND ca.external_system = 'civicrm_contribution'
WHERE
c.is_test = 0 AND c.contribution_status_id = 1 and c.contribution_recur_id IS NULL


