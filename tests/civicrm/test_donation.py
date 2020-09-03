from keanu import BatchTestCase

class TestDonation(BatchTestCase):
    ORDER = "36"

    def test_change_of_receive_date(_):
        cividb = _.batch.find_source_by_name('testset')
        cividb.use()

        # Would probably make sense to turn connection() to a @property
        contrib_id, = cividb.connection().execute('SELECT id FROM civicrm_contribution WHERE contribution_status_id = 4 ORDER BY RAND() LIMIT 1').fetchone()
        cividb.connection().execute('UPDATE civicrm_contribution SET receive_date = NOW() WHERE id = {} LIMIT 1'.format(contrib_id))

        _.batch.destination.use()

        _.incremental_load(TestDonation.ORDER)

        count, = _.connection.execute('SELECT COUNT(*) FROM payment WHERE external_id = {}'.format(contrib_id)).fetchone()

        _.assertEqual(count, 1)
