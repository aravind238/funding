from flask import abort
from datetime import datetime, timedelta
from pytz import timezone
import time


def utc_to_local(remove_microseconds=True, iso_format=True, tz="US/Eastern", dt=None):
    """[summary]

    Args:
        remove_microseconds (bool, optional): [removes microseconds]. Defaults to True.
        iso_format (bool, optional): [iso format]. Defaults to True.
        tz (str, optional): [timezone]. Defaults to "US/Eastern".
        dt (datetime, required): [datetime]. Defaults to None.

    Returns: current datetime based off timezone(tz)
    """
    if not dt:
        # return abort(400, "Variable dt is empty.")
        dt = datetime.utcnow().isoformat()

    # convert to timezone tz
    to_tz = timezone(tz)
    # utc timezone
    utc = timezone("UTC")
    fmt = "%Y-%m-%dT%H:%M:%S"
    fmt_tz = "%Y-%m-%dT%H:%M:%S%z"

    # .fromisoformat() method is to load an iso formatted datetime string into a python datetime object
    str_to_datetime = datetime.fromisoformat(dt)

    # return str_to_datetime.replace(tzinfo=utc).astimezone(to_tz).strftime(fmt)

    result = str_to_datetime.replace(tzinfo=utc)
    # remove_microseconds = True: to remove the microseconds
    if remove_microseconds:
        result = result.replace(microsecond=0)

    result = result.astimezone(to_tz)

    # iso_format = True: get datetime in isoformat
    if iso_format:
        result = result.isoformat()

    return result


def current_date(tz="US/Eastern"):
    """[summary]

    Args:
        tz (str, optional): [timezone]. Defaults to "US/Eastern".

    Returns: current date
    """
    # current datetime
    current_datetime = utc_to_local(
        iso_format=False, tz=tz, dt=datetime.utcnow().isoformat()
    )
    return current_datetime.date()


def previous_date(tz="US/Eastern", day=1):
    """[summary]

    Args:
        tz (str, optional): [timezone]. Defaults to "US/Eastern".
        day (int, optional): [day]. Defaults to 1.

    Returns: previous date from current date
    """
    return current_date(tz=tz) - timedelta(days=day)


def next_date(tz="US/Eastern", day=1):
    """[summary]

    Args:
        tz (str, optional): [timezone]. Defaults to "US/Eastern".
        day (int, optional): [day]. Defaults to 1.

    Returns: next date from current date
    """
    return current_date(tz=tz) + timedelta(days=day)


def date_concat_time(tz="US/Eastern", time_concat="04:00:00", date_concat="current"):
    """[summary]

    Args:
        tz (str, optional): [timezone]. Defaults to "US/Eastern".
        time_concat (str, optional): [time to be concatenated]. Defaults to "04:00:00".
        date_concat (str, optional): [date to be concatenated]. Defaults to "current".

    Returns: concatenated date and time
    """
    date_concat_list = ["previous", "current", "next"]
    if date_concat not in date_concat_list:
        abort(400, f"date_concat should be from list {date_concat_list}")

    # check time format
    is_hh_mm_time(time_string=time_concat)

    datetime_concat = f"{current_date(tz=tz)} {time_concat}"
    if date_concat == "previous":
        datetime_concat = f"{previous_date(tz=tz)} {time_concat}"

    if date_concat == "next":
        datetime_concat = f"{next_date(tz=tz)} {time_concat}"

    return datetime_concat


def is_hh_mm_time(time_format="%H:%M:%S", time_string=None):
    """[summary]

    Args:
        time_format (str, optional): [time in string format]. Defaults to "%H:%M:%S".
        time_string (required): [description]. Defaults to None.

    Returns: returns True or False
    """
    if not time_string:
        abort(400, f"time_string cannot be null")

    try:
        time.strptime(time_string, time_format)
    except Exception as e:
        return abort(400, str(e))

    return True


def datetime_to_string_format(
    remove_microseconds=True, tz="US/Eastern", fmt="%Y-%m-%dT%H:%M:%S"
):
    """[summary]

    Args:
        remove_microseconds (bool, optional): [remove microseconds]. Defaults to True.
        tz (str, optional): [timezone]. Defaults to "US/Eastern".
        fmt (str, optional): [string format]. Defaults to "%Y-%m-%dT%H:%M:%S".

    Returns: datetime obj to string format based off format(fmt)
    """
    # datetime object
    datetime_obj = utc_to_local(
        remove_microseconds=remove_microseconds,
        iso_format=False,
        tz=tz,
        dt=datetime.utcnow().isoformat(),
    )
    # convert a datetime object to string format
    date_time = datetime_obj.strftime(fmt)
    return date_time
