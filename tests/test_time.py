import unittest
from freezegun import freeze_time
from notification_backend.time import get_epoch_time
from notification_backend.time import get_current_epoch_time


class TestTime(unittest.TestCase):

    @freeze_time("2016-01-01")
    def test_get_current_epoch_time(self):
        c_time = get_current_epoch_time()
        self.assertEqual(c_time, 1451606400)

    def test_get_epoch_time(self):
        iso_str = "2016-04-12T01:40:17Z"
        c_time = get_epoch_time(iso_str)
        self.assertEqual(c_time, 1460425217)
