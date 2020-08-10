from keanu import BatchTestCase

class TestContact(BatchTestCase):
    ORDER = "5"

    def test_contact_count(_):
        contact_count = _.connection.execute("SELECT count(*) FROM contact").fetchone()[0]
        _.assertEqual(contact_count, 2493)

    def test_change_of_preferred_language(_):
        # XXX
        # this is a bit cumbersome but we have the batch under _.batch and also
        # copy of _.batch.destination.connectio() in _.connection... maybe it
        # would be better to make batch accessors easier to use and use it
        # directly
        cividb = _.batch.find_source_by_name('testset')
        cividb.use()

        # Would probably make sense to turn connection() to a @property
        cividb.connection().execute('UPDATE civicrm_contact SET preferred_language = "de_DE" where id = 61')

        _.batch.destination.use()

        _.incremental_load("5")

        id, pref = _.connection.execute('SELECT id,preferred_language FROM contact where id = 61').fetchone()

        _.assertEqual(id, 61)
        _.assertEqual(pref, "de_DE")
