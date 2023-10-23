from datetime import datetime
import logging
import os, time
from logging.handlers import RotatingFileHandler
from src.resources.v2.helpers.convert_datetime import (
    datetime_to_string_format,
    utc_to_local,
)


class Logs:
    def __init__(
        self, save_as_file=True, log_level_name="info", filename="funding", data={}
    ) -> None:
        self.save_as_file = save_as_file
        self.log_level_name = log_level_name
        self.data = data
        self.filename = f'{filename}_{datetime_to_string_format(fmt="%Y-%m-%d")}.log'

        # ToDo: Need to convert time to est
        # # convert logging datetime
        # logging.Formatter.converter = datetime.utcnow().timetuple()

        # the parent directory (ie /var/www/funding-backend-flask)
        self.parent_path = os.getcwd()
        self.parent_logs_path = os.path.join(self.parent_path, "logs")
        self.create_folder()

        # now we can build the file path
        self.file_path = os.path.join(self.parent_logs_path, self.filename)

        if not log_level_name:
            self.log_level_name = "info"

    def create_folder(self):
        try:
            if not os.path.exists(self.parent_logs_path):
                os.makedirs(self.parent_logs_path)
        except OSError:
            print("Error: Creating directory. " + self.parent_logs_path)

    def save_logs(self):
        if not self.save_as_file:
            self.save_logs_in_aws()
        else:
            self.save_logs_in_file()

    @property
    def set_logger(self):
        # # rfh = RotatingFileHandler(
        # #     filename=self.file_path,
        # #     maxBytes=10*1024*1024,
        # #     backupCount=5,
        # # )
        # logging.basicConfig(
        #     filename=self.file_path,
        #     level=logging.DEBUG,
        #     format=f"%(asctime)s - %(levelname)s - %(name)s : %(message)s",
        #     datefmt="%Y-%m-%d %H:%M:%S",
        #     # handlers=[
        #     #     rfh
        #     # ],
        # )
        logger = logging.getLogger(name=self.filename)
        logger.setLevel(logging.INFO)

        # create a file handler
        file_handler = logging.FileHandler(self.file_path)
        file_handler.setLevel(logging.INFO)

        # create a logging format
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(name)s : %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        # delete all the elements in the logger.handlers
        del logger.handlers[:]

        # add the handlers to the logger
        logger.addHandler(file_handler)
        return logger

    @property
    def error_log(self):
        self.set_logger.error(f"{self.data}")

    @property
    def info_log(self):
        self.set_logger.info(f"{self.data}")

    @property
    def warning_log(self):
        self.set_logger.warning(f"{self.data}")

    @property
    def log_level(self):
        if self.log_level_name == "error":
            self.error_log
        elif self.log_level_name == "warning":
            self.warning_log
        else:
            self.info_log

    def save_logs_in_file(self):
        self.log_level

    def save_logs_in_aws(self):
        print("--save logs in aws--", self.data)
        pass
