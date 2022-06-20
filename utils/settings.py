LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'file_formatter': {
            'format': '[{levelname}: {asctime}] [{module}:{funcName}:{lineno}]: "{message}"',
            'style': '{'
        },
        'debug_formatter': {
            'format': '[{levelname}] [{module}:{funcName}:{lineno}]: "{message}"',
            'style': '{'
        }
    },

    'handlers': {
        'console_handler': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  # Default is stderr
            'formatter': 'debug_formatter',
        },
        'file_handler': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'temp/logs/debug.log',
            'mode': 'a',  # default 'a'
            'encoding': 'utf-8',
            'formatter': 'file_formatter',
        }
    },

    'loggers': {
        # '': {  # root logger
        #     'handlers': ['console_handler', 'file_handler'],
        #     'level': 'DEBUG',
        #     'propagate': False
        # },
        'logger': {
            'handlers': ['console_handler', 'file_handler'],
            'level': 'DEBUG',
            'propagate': False
        },
        # '__main__': {  # if __name__ == '__main__'
        #     'handlers': ['console_handler', 'file_handler'],
        #     'level': 'DEBUG',
        #     'propagate': False
        # },
        'site_parsers.sol.sol_book': {
            'handlers': ['console_handler', 'file_handler'],
            'level': 'DEBUG',
            'propagate': False
        },
        'site_parsers.sol.sol_request_authorization': {
            'handlers': ['console_handler', 'file_handler'],
            'level': 'INFO',
            'propagate': False
        },
        'site_parsers.sol.sol_requests_soup': {
            'handlers': ['console_handler', 'file_handler'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}
