import os
import json
import sys
import os.path as p
import logging
import logging.config
import traceback
import datetime as dt
from datetime import timezone
from functools import wraps

PACKAGE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def configurable(config_path=None):
    def _decorator(function):
        @wraps(function)
        def config_wrapper(*args, **kwargs):
            sys.excepthook = except_hook

            application_config = _get_application_config(config_path)

            logging_config = _get_logging_config()
            logging.config.dictConfig(logging_config)

            kwargs['application_config'] = application_config

            return function(*args, **kwargs)

        return config_wrapper

    return _decorator


def except_hook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    exception = traceback.format_exception(exc_type, exc_value, exc_traceback)

    logger.critical(f"Uncauhgt exception occured, application will terminate: {exception}",
                    exc_info=(exc_type, exc_value, exc_traceback))


def _get_application_config(json_config_path) -> dict:
    json_config_dir = p.dirname(sys.argv[0])

    if json_config_path is None:
        json_config_path = p.join(json_config_dir, 'application_config.json')
    else:
        if not p.isabs(json_config_path):
            json_config_path = p.join(json_config_dir, json_config_path)

    if not p.isfile(json_config_path):
        raise FileNotFoundError(json_config_path)

    with open(json_config_path, "r") as config_file:
        application_config = json.loads((config_file.read()))

    if not 'meta' in application_config:
        raise KeyError(f"Meta mandatory section in {application_config} not found")

    if not {"service_name", "version"} <= set(application_config['meta']):
        raise KeyError(f"One of mandatory keys (service_name, version) in Meta is not found")

    return application_config


def _get_logging_config() -> dict:
    with open(os.path.join(PACKAGE_ROOT_DIR, "logging_config.json"), "r") as read_file:
        log_dict = json.load(read_file)
    return log_dict


def utc_to_local(utc_dt):
    return dt.datetime.strptime(utc_dt, "%Y-%m-%dT%H:%M:%S%z") \
        .replace(tzinfo=timezone.utc) \
        .astimezone(tz=None) \
        .replace(tzinfo=None)
