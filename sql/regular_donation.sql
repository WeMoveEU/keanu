-- regular donations
-- +-------------------+---------------+------+-----+---------+----------------+
-- | Field             | Type          | Null | Key | Default | Extra          |
-- +-------------------+---------------+------+-----+---------+----------------+
-- | id                | int(11)       | NO   | PRI | NULL    | auto_increment |
-- | amount            | decimal(10,2) | NO   |     | NULL    |                |
-- | total_amount      | decimal(16,2) | NO   |     | NULL    |                |
-- | original_currency | varchar(3)    | NO   |     | NULL    |                |
-- | original_amount   | varchar(32)   | NO   |     | NULL    |                |
-- | provider          | int(11)       | NO   |     | NULL    |                |
-- | contact_action_id | int(11)       | NO   | MUL | NULL    |                |
-- | ended_at          | datetime      | YES  |     | NULL    |                |
-- | payment_count     | int(11)       | NO   |     | 0       |                |
-- | failure_count     | varchar(32)   | NO   |     | 0       |                |
-- +-------------------+---------------+------+-----+---------+----------------+


INSERT INTO regular_donation
(amount,total_amount,original_currency,original_amount,provider,contact_action_id, ended_at,
payment_count,failure_count)

SELECT
  amount,
  total_amount,
  original_currency,
  original_amount,
  CASE WHEN payment_instrument_id = 1 THEN 'paypal'
       WHEN payment_instrument_id = 2 THEN 'card'
       WHEN payment_instrument_id in (6,7) THEN 'sepa'
  END as provider,
  contact_action_id,
  CASE WHEN end_date is not null then end_date
       ELSE
         CASE WHEN DATEDIFF(CURDATE(), last_payment_date) > 60
              THEN last_payment_date
              ELSE NULL
         END
  END as ended_at,
  payment_count,
  failure_count

FROM ( -- x 
---- FIRSTLY, NON-STRIPE
SELECT
ca.id as contact_action_id,
rd.amount as original_amount,
rd.currency as original_currency,
rd.amount,
rd.end_date,
rd.failure_count,
rd.payment_instrument_id,
sum(c.total_amount) as total_amount,
count(c.id) as payment_count,
max(c.receive_date) as last_payment_date

FROM wemove_47.civicrm_contribution_recur rd
JOIN contact_action ca ON rd.id = ca.external_id
JOIN wemove_47.civicrm_contribution c ON c.contribution_recur_id = rd.id

WHERE c.contribution_status_id = 1 and c.is_test = 0
AND c.payment_instrument_id in (1, 6, 7)  -- no stripe here
GROUP BY 1,2,3,4,5,6,7  

-- now union stripe
UNION

SELECT
ca.id as contact_action_id,
rd.amount as original_amount,
rd.currency as original_currency,
rd.amount,
rd.end_date,
rd.failure_count,
rd.payment_instrument_id,
sum(sp.amount) as total_amount,
count(sp.id) as payment_count,
max(sp.created_date) as last_payment_date

FROM wemove_47.civicrm_contribution_recur rd
JOIN contact_action ca ON rd.id = ca.external_id
JOIN stripe_payments sp 
    ON sp.card_id = (SELECT px.card_id FROM stripe_payments px
                     JOIN wemove_47.civicrm_contribution cx ON px.id = cx.trxn_id
                     WHERE cx.contribution_recur_id = rd.id
                       AND cx.contribution_status_id=1 AND cx.is_test = 0
                     LIMIT 1)
    AND sp.status = 'Paid'


WHERE rd.payment_instrument_id = 2 

GROUP BY 1,2,3,4,5,6,7

) x

;

