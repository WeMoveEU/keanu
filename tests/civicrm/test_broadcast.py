from keanu import BatchTestCase

class TestBroadcast(BatchTestCase):
    ORDER = "51"

    def test_ask_type(_):
        type_count = _.connection.execute("SELECT COUNT(DISTINCT ask_type) FROM broadcast").fetchone()[0]
        _.assertTrue(type_count > 1)

    def test_incremental_update(_):
        # XXX
        # this is a bit cumbersome but we have the batch under _.batch and also
        # copy of _.batch.destination.connectio() in _.connection... maybe it
        # would be better to make batch accessors easier to use and use it
        # directly
        cividb = _.batch.find_source_by_name('testset')
        cividb.use()

        # Would probably make sense to turn connection() to a @property
        cividb.connection().execute("UPDATE civicrm_value_mailingdata SET mailing_ask_type = 'noop_watch' where entity_id = 18536")

        _.batch.destination.use()

        _.incremental_load(TestBroadcast.ORDER)

        ask_type, = _.connection.execute('SELECT ask_type FROM broadcast where id = 18536').fetchone()

        _.assertEqual(ask_type, "noop_watch")
