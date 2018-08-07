import json
import logging
import sys
import requests

from influxdb import InfluxDBClient
from threading import Timer
from websocket import WebSocketApp

global LOGGER
LOGGER = None


def get_verbosity(verbosity):
    return {
        0: logging.ERROR,
        1: logging.WARN,
        2: logging.INFO,
        3: logging.DEBUG,
        None: logging.WARN,
    }.get(verbosity, logging.DEBUG)


def get_logger(verbosity=2, log_file="/tmp/mqtt_otgw.log"):
    global LOGGER

    if LOGGER:
        return LOGGER

    log_format = "[%(asctime)s] %(name)s | %(funcName)-20s | %(levelname)s | %(message)s"
    logging.basicConfig(filename=log_file, level=logging.INFO, filemode="w", format=log_format)
    logger = logging.getLogger('mqtt_otgw')

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(logging.Formatter(fmt=log_format))

    if not logger.handlers:
        logger.setLevel(get_verbosity(verbosity))
        logger.addHandler(stream_handler)

    LOGGER = logger

    return logger


def is_a_number(s):
    """ Tests if S is a number.
    """
    try:
        float(s)
        return True
    except ValueError:
        return False


def fetch_otmonitor_status(settings):
    """ Fetch otmonitor status.
    """
    response = requests.get(settings.otmonitor_url, timeout=5)
    status = response.json()

    logging.info("otmonitor.response: %s -> %s" % (response, status))

    result = dict()

    flame = 0
    if 'flame' in status:
        flame = int(status['flame']['value'])

    for key in status:
        if "value" in status[key]:
            value_s = status[key]['value']

            if key == 'modulation':
                if flame == 1 and is_a_number(value_s):

                    v = float(value_s)
                    rml = settings.min_modulation + (
                                (settings.max_modulation - settings.min_modulation) * (float(v) / 100))
                    v = round(rml, 0)
                else:
                    v = None

                result[key] = v

            else:
                if is_a_number(value_s):
                    result[key] = float(value_s)
                else:
                    result[key] = None

    send_to_influxdb(settings, result)


def send_to_influxdb(settings, fields):
    req = {
        "measurement": settings.influx_measurement,
        "tags": {},
        "fields": {}
    }

    if settings.influx_tags:
        for tag in settings.influx_tags:
            tag_kv = tag.split('=')
            req['tags'][tag_kv[0]] = tag_kv[1]

    for field_k, field_v in fields.items():
        if field_v is not None:
            req['fields'][field_k] = field_v

    logging.info("InfluxDB.request: %s" % req)

    reqs = [req]

    client = InfluxDBClient(host=settings.influx_hostname,
                            port=settings.influx_port,
                            username=settings.influx_username,
                            password=settings.influx_password,
                            database=settings.influx_database)

    client.write_points(reqs, retention_policy=settings.influx_retention_policy, database=settings.influx_database)


def start_scheduler(settings):
    """ Start the scheduler.
    """

    def monitor_status():
        fetch_otmonitor_status(settings)
        ws = WebSocketApp(settings.otmonitor_websocket_url, on_message=ws_on_message)
        ws.run_forever(ping_interval=10)

    def ws_on_message(ws, message):
        logging.info("WebSocket -> otmonitor - onMessage(%s)" % message)

        message_j = json.loads(message)

        for result in message_j["status"].keys():
            logging.debug('OTGW.received.status.key: %s' % result)
            if result in settings.status_keys:
                fetch_otmonitor_status(settings)

    def schedule_fetch_otmonitor_status():
        """ Schedule the timer_add_Status_to_queue function.
        """
        # noinspection PyBroadException
        def timer_fetch_otmonitor_status():
            """
            Adds the last_known_status to the status_queue.
            """
            try:
                fetch_otmonitor_status(settings)
            except Exception:
                pass
            schedule_fetch_otmonitor_status()

        u = Timer(interval=settings.poller_wait_time, function=timer_fetch_otmonitor_status)
        u.daemon = True
        u.start()

    schedule_fetch_otmonitor_status()
    monitor_status()
