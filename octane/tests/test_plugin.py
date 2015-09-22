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

import json
from octane.util import plugin


def test_check_plugin():
    data = json.loads(CLUSTER_SETTINGS_SAMPLE)
    assert plugin.__is_present(data, 'emc_vnx') is True
    assert plugin.__is_enabled(data, 'emc_vnx') is True


CLUSTER_SETTINGS_SAMPLE = """
{
  "editable": {
    "zabbix_monitoring_emc": {
      "hosts": {
        "value": "",
        "type": "text",
        "description": "comma separated NAME:IP values",
        "weight": 10,
        "label": "EMC hardware to monitor"
      },
      "metadata": {
        "restrictions": [
          {
            "action": "disable",
            "message": "This plugin requires SNMP trap daemon for Zabbix plugin",
            "condition": "settings:zabbix_snmptrapd.metadata.enabled == false"
          }
        ],
        "weight": 70,
        "enabled": false,
        "label": "EMC hardware monitoring extension for Zabbix plugin",
        "toggleable": true,
        "plugin_id": 3
      }
    },
    "emc_vnx": {
      "emc_sp_a_ip": {
        "regex": {
          "source": "^(?:(?0-4][0-9]|[01]?[0-9][0-9]?)$",
          "error": "Specify valid IPv4 address"
        },
        "description": "EMC VNX Service Processor A IP address.",
        "weight": 90,
        "value": "192.168.200.30",
        "label": "EMC VNX SP A IP",
        "type": "text"
      },
      "emc_sp_b_ip": {
        "regex": {
          "source": "^(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
          "error": "Specify valid IPv4 address"
        },
        "description": "EMC VNX Service Processor B IP address.",
        "weight": 90,
        "value": "192.168.200.31",
        "label": "EMC VNX SP B IP",
        "type": "text"
      },
      "emc_password": {
        "regex": {
          "source": "S",
          "error": "Password field cannot be empty"
        },
        "description": "EMC VNX password.",
        "weight": 80,
        "value": "password",
        "label": "EMC VNX password",
        "type": "password"
      },
      "emc_username": {
        "regex": {
          "source": "S",
          "error": "Username field cannot be empty"
        },
        "description": "EMC VNX username.",
        "weight": 75,
        "value": "username",
        "label": "EMC VNX username",
        "type": "text"
      },
      "emc_pool_name": {
        "value": "",
        "type": "text",
        "description": "EMC VNX pool name (optional)",
        "weight": 95,
        "label": "EMC VNX pool name"
      },
      "metadata": {
        "plugin_id": 1,
        "enabled": true,
        "toggleable": true,
        "weight": 70,
        "label": "EMC VNX driver for Cinder"
      }
    }
  }
}
"""[1:]  # noqa
