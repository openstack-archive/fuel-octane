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
        new_env = self.client.connection.post_request(
            "clusters/{0}/upgrade/clone".format(parsed_args.id),
            {
                'name': parsed_args.name,
                'release_id': parsed_args.release,
            }
        )
        new_env = data_utils.get_display_data_single(self.columns, new_env)
        return (self.columns, new_env)
