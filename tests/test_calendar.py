from keanu import BatchTestCase

class TestCalendar(BatchTestCase):
    def setUp(_):
        _.full_load("2")

    def test_birthday_weekday(_):
        dayno, dayname = _.connection.execute("SELECT dw, day_name FROM calendar WHERE dt = '2020-07-28'").fetchone()
        _.assertEqual(dayno,  3)
        _.assertEqual(dayname, "Tuesday")
