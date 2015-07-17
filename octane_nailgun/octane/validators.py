from nailgun.api.v1.validators import base


class ClusterCloneValidator(base.BasicValidator):
    single_schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Cluster Clone Parameters",
        "description": "Serialized parameters to clone clusters",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "release_id": {"type": "number"},
        },
    }


class UpgradeNodeAssignmentValidator(base.BasicValidator):
    single_schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Assign Node Parameters",
        "description": "Serialized parameters to assign node",
        "type": "object",
        "properties": {
            "node_id": {"type": "number"},
        },
    }
