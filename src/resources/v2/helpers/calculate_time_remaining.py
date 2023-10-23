from src.resources.v2.helpers import custom_response
from src.middleware.authentication import Auth
from datetime import datetime
from pytz import timezone
from src.middleware.permissions import Permissions



def calculate_time_remaining(**kwargs):
    """
    ================
    date_format:
    ================
    date_format = "%H:%M:%S" for time format

    ================
    datetime_timezone:
    ================
    for timezone i.e 'US/Eastern'

    ================
    diff_in:
    ================
    diff_in = "h" for difference in hours
    diff_in = "m" for difference in minutes
    diff_in = "s" for difference in seconds

    ================
    time_start/time_end:
    ================
    time_start/time_end is needed for calculating based off time
    """
    try:       
        date_format = "%H:%M:%S"
        datetime_timezone = kwargs.get("datetime_timezone", "US/Eastern")
        diff_in = kwargs.get("diff_in", "s")
        time_start = kwargs.get("time_start", None)
        time_end = kwargs.get("time_end", None)            

        diff = None
        diff_result = None
        status_code = 400
        msg = None

        # time_start/time_end is required
        if time_start is None and time_end is None:
            status_code = 404
            msg = "time_start/time_end is required."

        diff_in_obj = {
            "h": "hours",
            "m": "minutes",
            "s": "seconds",
        }
        if diff_in in diff_in_obj:
            diff_in = diff_in_obj[diff_in]
        else:
            diff_in = "seconds"
        
        # current utc date time
        current_utc_datetime = datetime.now(timezone("UTC"))
        current_datetime = current_utc_datetime

        # convert utc to datetime timezone
        if datetime_timezone:
            current_datetime = current_utc_datetime.astimezone(timezone(datetime_timezone))

        # current time based off timezone
        current_time = current_datetime.strftime(date_format)

        try:
            # You could also pass datetime.time object in this part and convert it to string.
            if time_start and time_end is None:
                time_start = str(time_start)
                diff = current_datetime.strptime(current_time, date_format) - current_datetime.strptime(time_start, date_format)

            if time_end and time_start is None:
                time_end = str(time_end)
                diff = current_datetime.strptime(time_end, date_format) - current_datetime.strptime(current_time, date_format)            
        except Exception as e:
            msg = str(e)

        if diff:
            # Get the time in seconds i.e. 5120
            diff_result = diff.total_seconds()
            status_code = 200
            msg = "Remaining time calculated successfully"

            # Get the time in minutes i.e. 120.4, 756.2
            if diff_in == "minutes":
                diff_result = diff.total_seconds() / 60

            # Get the time in hours i.e. 9.60, 8.5
            if diff_in == "hours":
                diff_result = diff.total_seconds() / 3600

        if status_code != 200:
            diff_result = msg

        result = {
            "status_code": status_code,
            "msg": msg,
            "date_format": date_format,
            "timezone": datetime_timezone,
            "diff_in": diff_in,
            "current_datetime": current_datetime.isoformat(),
            "diff": diff_result
        }

        return result

    except Exception as e:
        print(f"cal_time_remaining Exception: {e}")
        return custom_response({"status": "error", "msg": str(e)}, 404)
