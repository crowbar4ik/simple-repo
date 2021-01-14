import argparse
import logging.config
from utils.common import configurable
from github_integration.github_data_loader_processing import GitHubDataLoaderProcessing

__author__ = 'Alexey.Ak'
__version__ = '0.1'

logger = logging.getLogger('startlight')
logger.propagate = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GiHub API data loader')

    @configurable()
    def start(application_config):
        logger.info("Application Started")
        app = GitHubDataLoaderProcessing(application_config)
        app.run()
        logger.info("Application finished")

    start()
