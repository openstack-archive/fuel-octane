# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging


class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: '\033[00;32m',  # GREEN
        logging.INFO: '\033[00;36m',  # CYAN
        logging.WARN: '\033[01;33m',  # BOLD YELLOW
        logging.ERROR: '\033[01;31m',  # BOLD RED
        logging.CRITICAL: '\033[01;31m',  # BOLD RED
    }

    def format(self, record):
        res = logging.Formatter.format(self, record)  # old-style class on 2.6
        return self.LEVEL_COLORS[record.levelno] + res + '\033[m'


def set_console_formatter(**formatter_kwargs):
    root_logger = logging.getLogger('')
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            console_handler = handler
            break
    else:
        return  # Didn't find any StreamHandlers there
    formatter = ColorFormatter(**formatter_kwargs)
    console_handler.setFormatter(formatter)


def silence_iso8601():
    iso8601_logger = logging.getLogger('iso8601')
    iso8601_logger.setLevel(logging.INFO)
