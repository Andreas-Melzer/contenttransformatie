import sys
import logging
import logging.config

LOG_SETTINGS = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
        "json_simulated": {
            # A simple format that looks like JSON for easier parsing in Kibana/Loki
            "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        }
    },
    "handlers": {
        "console_standard": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": sys.stdout,
        },
        "console_json": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "json_simulated",
            "stream": sys.stdout,
        },
    },
    "loggers": {
        # The root logger catches everything else
        "": {
            "handlers": ["console_standard"],
            "level": "INFO",
            "propagate": True,
        },
        # Your specific application logger
        "Contenttransformatie": {
            "handlers": ["console_json"], 
            "level": "DEBUG",
            "propagate": False,
        },
    }
}

class LogBootstrap:
    """
    Handles the initialization of the logging configuration.
    Designed to support external configuration injection via ConfigMaps in OpenShift/K8s.
    """

    @staticmethod
    def load_config():
        logging.config.dictConfig(LOG_SETTINGS)
