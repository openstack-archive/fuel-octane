from setuptools import find_packages
from setuptools import setup


setup(name="octane_fuelclient",
      version="0.0.0",
      packages=find_packages(),
      zip_safe=False,
      entry_points={
          'fuelclient': [
              'env_clone = octaneclient.commands:EnvClone',
              'env_assign_node = octaneclient.commands:EnvAssignNode',
              ]
          }
      )
