import logging


def get_logger():
    logger = logging.getLogger("celery")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = get_logger()


def get_celery_config(config):
    celery_config = config.CELERY

    settings = {
        "broker_url": celery_config.BROKER_URL,
        "result_backend": celery_config.RESULT_BACKEND,

        "task_serializer": celery_config.TASK_SERIALIZER,
        "accept_content": celery_config.ACCEPT_CONTENT,
        "result_serializer": celery_config.RESULT_SERIALIZER,

        "timezone": celery_config.TIMEZONE,
        "enable_utc": celery_config.ENABLE_UTC,

        "task_acks_late": celery_config.TASK_ACKS_LATE,
        "task_reject_on_worker_lost": celery_config.TASK_REJECT_ON_WORKER_LOST,

        "worker_prefetch_multiplier": celery_config.WORKER_PREFETCH_MULTIPLIER,
        "worker_concurrency": celery_config.WORKER_CONCURRENCY,

        "result_expires": celery_config.RESULT_EXPIRES,

        "broker_connection_retry_on_startup": celery_config.BROKER_CONNECTION_RETRY_ON_STARTUP,
        "broker_connection_max_retries": celery_config.BROKER_CONNECTION_MAX_RETRIES,

        "task_default_queue": celery_config.TASK_DEFAULT_QUEUE,

        "task_routes": {
            'stock_crawler.crawl_stock_info': {'queue': 'trader.stock.info'},
            'stock_crawler.crawl_stock_price': {'queue': 'trader.stock.price'},
        },

        "task_default_delivery_mode": "persistent",
    }

    return settings
