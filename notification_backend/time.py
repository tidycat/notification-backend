import iso8601
import datetime
import pytz


def get_epoch_time(iso8601_str):
    epoch_datetime = datetime.datetime(1970, 1, 1)
    epoch_datetime = epoch_datetime.replace(tzinfo=pytz.UTC)
    datetime_obj = iso8601.parse_date(iso8601_str)
    return_val = (datetime_obj - epoch_datetime).total_seconds()
    return int(return_val)


def get_current_epoch_time():
    epoch_datetime = datetime.datetime(1970, 1, 1)
    epoch_datetime = epoch_datetime.replace(tzinfo=pytz.UTC)
    now_datetime = datetime.datetime.utcnow()
    now_datetime = now_datetime.replace(tzinfo=pytz.UTC)
    return_val = (now_datetime - epoch_datetime).total_seconds()
    return int(return_val)
