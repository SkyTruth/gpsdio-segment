import json
import random

import dateutil.parser
import pytz


def utcify(msg):
    if "timestamp" in msg:
        msg = msg.copy()
        if msg["timestamp"].tzinfo is None:
            msg["timestamp"] = pytz.utc.localize(msg["timestamp"])
        else:
            msg["timestamp"] = msg["timestamp"].astimezone(pytz.utc)
    return msg


def add_type_field(msgs):
    for x in msgs:
        if "type" not in x:
            x["type"] = "UNKNOWN"


def read_json(src, add_msgid=True, add_type=True):
    for x in src:
        x = x.strip()
        if x:
            msg = json.loads(x)
            if "timestamp" in msg:
                msg["timestamp"] = dateutil.parser.parse(msg["timestamp"])
            msg = utcify(msg)
            if add_msgid and "msgid" not in msg:
                msg["msgid"] = random.random()
            if add_type and "type" not in msg:
                msg["type"] = "UNKNOWN"
            yield msg
