#!/usr/bin/env python

"""
Script to generate sql for the LandingZone
"""

from pathlib import Path

import datetime
import jinja2
import json
import logging
import mimetypes
import os
import smtplib
import sys

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


"""
Constants
"""
DEFAULT_LOGS_DIR = "logs"
# DEFAULT_LOG_FORMAT = "%(asctime)s-%(levelname)s %(message)s"
DEFAULT_LOG_MSG_FORMAT = (
    "%(asctime)s:%(filename)s:%(funcName)s-%(levelname)s %(message)s"
)
DEFAULT_LOG_DATE_FORMAT = "%d-%m-%YT%H:%M:%S"

"""
"""


def checkDir(dirName):
    Path(dirName).mkdir(exist_ok=True)


"""
return true if the line is a comment
"""


def is_comment(line):
    return line.startswith("#")


"""
returns true if the line contain only spaces
"""


def is_whitespace(line):
    return line.isspace()


"""
removes all comments from each line in lines
"""


def decomment(lines):
    for line in lines:
        if not is_comment(line) and not is_whitespace(line):
            yield line


"""
"""


def read_file(fn, mode):
    with open(fn, mode) as fh:
        data = fh.read()
    return data


"""
reads a json file and returns a dict
"""


def read_json(fn):
    with open(fn) as json_file:
        return json.load(json_file)

"""
writes a dict as a json file
"""

def write_json(data_dict, fn):
    with open(fn, 'w') as json_file:
        json.dump(data_dict, json_file, indent=4)



"""
reads a jinja2 file and returns a template
"""


def read_j2_template(fn):
    with open(fn) as fh:
        return jinja2.Template(fh.read())


"""
"""


def write_text_to_file(out_fn, text):
    with open(out_fn, "w") as fh:
        fh.write(text)


"""
writes into a file the result of rendering the jinja2  with data
"""


def write_j2_template(out_fn, j2_template, data):
    with open(out_fn, "w") as fh:
        fh.write(j2_template.render(data))


"""
"""


def initRootLogger(
    logsDirName=None, log_msg_format=None, log_date_format=None, debug=False
):
    if not logsDirName:
        logsDirName = DEFAULT_LOGS_DIR
    checkDir(logsDirName)
    # Formatter
    if not log_msg_format:
        log_msg_format = DEFAULT_LOG_MSG_FORMAT
    if not log_date_format:
        log_date_format = DEFAULT_LOG_DATE_FORMAT
    logFormatter = logging.Formatter(fmt=log_msg_format, datefmt=log_date_format)
    rootLogger = logging.getLogger()
    if debug:
        rootLogger.setLevel(logging.DEBUG)
    else:
        rootLogger.setLevel(logging.INFO)
    # fileHandler
    logScriptFilename = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    logDateTime = "{:%Y%m%dT%H%M%S}".format(datetime.datetime.now())
    fileHandler = logging.FileHandler(
        logsDirName + os.path.sep + logDateTime + "_" + logScriptFilename + ".log"
    )
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)
    # consoleHandler
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)
    return rootLogger


"""
"""


def send_mail(
    from_addr,
    to_addrs_list,
    subject,
    message_body,
    smtp_server="localhost",
    port=25,
    verbose=False,
    is_html=False,
    attachment_fn=None,
):
    outer = MIMEMultipart("alternative")
    outer["From"] = from_addr
    outer["To"] = ", ".join(to_addrs_list)
    outer["Subject"] = subject
    if is_html:
        body_part = MIMEText(message_body, "html")
    else:
        body_part = MIMEText(message_body, "plain")
    outer.attach(body_part)

    # attach file
    if attachment_fn:
        ctype, encoding = mimetypes.guess_type(attachment_fn)
        maintype, subtype = ctype.split("/", 1)
        if maintype == "text":
            with open(attachment_fn) as fp:
                att_part = MIMEText(fp.read(), _subtype=subtype)
        else:
            with open(attachment_fn, "rb") as fp:
                att_part = MIMEBase(maintype, subtype)
                att_part.set_payload(fp.read())
            encoders.encode_base64(att_part)
        att_part.add_header("Content-Disposition", "attachment", filename=attachment_fn)
        outer.attach(att_part)
    #
    composed = outer.as_string()
    with smtplib.SMTP(smtp_server, port) as server:
        if verbose:
            server.set_debuglevel(1)
        server.sendmail(from_addr, to_addrs_list, composed)
