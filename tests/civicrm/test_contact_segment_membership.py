from keanu import BatchTestCase

class TestContactSegmentMembership(BatchTestCase):
    ORDER = "40"

    def test_coverage(_):
        not_segmented = _.connection.execute("SELECT COUNT(*) FROM contact c LEFT JOIN contact_segment cs ON cs.contact_id=c.id AND cs.segmentation_id=2 WHERE cs.id IS NULL").fetchone()[0]
        _.assertEqual(not_segmented, 0)
