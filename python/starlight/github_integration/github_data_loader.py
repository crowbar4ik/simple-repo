import argparse
import logging.config
from utils.common import configurable
from utils.common import str2bool
from github_integration.github_data_loader_processing import GitHubDataLoaderProcessing

__author__ = 'Alexey.Ak'
__version__ = '0.1'

logger = logging.getLogger('startlight')
logger.propagate = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GiHub API data loader')
    parser.add_argument('-is_load', type=str2bool, required=True, help='Load data to the model: yes or no')
    parser.add_argument('-is_query', type=str2bool, required=True, help='Query data model: yes or no')
    args = parser.parse_args()

    @configurable()
    def start(application_config):
        logger.info("Application Started")
        app = GitHubDataLoaderProcessing(application_config, args.is_load, args.is_query)
        app.run()
        logger.info("Application finished")

    start()
