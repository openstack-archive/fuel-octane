from fuelclient.commands import base
from fuelclient.commands import environment as env_commands
from fuelclient.common import data_utils


class EnvClone(env_commands.EnvMixIn, base.BaseShowCommand):
    """Clone environment and translate settings to the given release."""

    columns = env_commands.EnvShow.columns

    def get_parser(self, prog_name):
        parser = super(EnvClone, self).get_parser(prog_name)
        parser.add_argument('name',
                            type=str,
                            help='Name of the new environment.')
        parser.add_argument('release',
                            type=int,
                            help='ID of the release of the new environment.')
        return parser

    def take_action(self, parsed_args):
        # TODO(akscram): While the clone procedure is not a part of
        #                fuelclient.objects.Environment the connection
        #                will be called directly.
        new_env = self.client._entity_wrapper.connection.post_request(
            "clusters/{0}/upgrade/clone".format(parsed_args.id),
            {
                'name': parsed_args.name,
                'release_id': parsed_args.release,
            }
        )
        new_env = data_utils.get_display_data_single(self.columns, new_env)
        return (self.columns, new_env)


class EnvAssignNode(env_commands.EnvMixIn, base.BaseCommand):
    """Add a node to an upgrade environment."""

    def get_parser(self, prog_name):
        parser = super(EnvAssignNode, self).get_parser(prog_name)
        parser.add_argument('id',
                            type=str,
                            help='ID of the environment.')
        parser.add_argument('node_id',
                            type=int,
                            help='ID of the node to upgrade.')
        return parser

    def take_action(self, parsed_args):
        # TODO(akscram): While the clone procedure is not a part of
        #                fuelclient.objects.Environment the connection
        #                will be called directly.
        self.client._entity_wrapper.connection.post_request(
            "clusters/{0}/upgrade/assign".format(parsed_args.id),
            {
                'node_id': parsed_args.node_id,
            }
        )
        msg = ('Node {node_id} successfully reassigned to the environment'
               ' {env_id}.\n'.format(
                   node_id=parsed_args.node_id,
                   env_id=parsed_args.id,
               ))
        self.app.stdout.write(msg)
