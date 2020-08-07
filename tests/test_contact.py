from keanu import BatchTestCase

class TestCalendar(BatchTestCase):
    ORDER = "5"

    def test_contact_count(_):
        contact_count = _.connection.execute("SELECT count(*) FROM contact").fetchone()[0]
        _.assertEqual(contact_count, 2493)
 
