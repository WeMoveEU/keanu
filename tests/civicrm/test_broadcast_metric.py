from keanu import BatchTestCase
from unittest import skip

class TestBroadcastMetric(BatchTestCase):
    ORDER = "56"

    def metric_value(_, broadcast_id, metric, segment_id=1):
        query = "SELECT value FROM broadcast_metric WHERE broadcast_id={} AND metric='{}' AND segment_id={}".format(broadcast_id, metric, segment_id)
        return _.connection.execute(query).fetchone()[0]

    def test_conversions_count(_):
        conversions_count = _.metric_value(29417, 'conversions')
        _.assertEqual(conversions_count, 12)

    @skip("Known bug in source data: https://trello.com/c/T6XOWTp2/114-mailing-association-of-civicrmredirect-donations")
    def test_civicrm_redirect_count(_):
        donations_count = _.metric_value(9729, 'monthly_donations')
        _.assertEqual(donations_count, 2)

    def test_donations_count(_):
        donations_count = _.metric_value(31577, 'oneoff_donations')
        conversions_count = _.metric_value(31577, 'conversions')
        _.assertEqual(conversions_count, 1)
        _.assertEqual(donations_count, 1)

