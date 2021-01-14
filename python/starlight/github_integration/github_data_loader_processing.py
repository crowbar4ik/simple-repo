import os
import requests
import logging
import datetime as dt
from sqlalchemy import create_engine
from snowflake.sqlalchemy import URL
from model import Base, PullRequests, PullRequestsFiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func
from jinjasql import JinjaSql
from utils.common import utc_to_local

logger = logging.getLogger("startlight")
PACKAGE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class GitHubDataLoaderProcessing:

    def __init__(self, application_config):
        self.github_common = application_config["github_common"]
        self.engine = create_engine(URL(**application_config["snowflake_connection"]))
        self.jinja_format = JinjaSql(param_style='pyformat')
        self.headers = {'Authorization': 'Bearer ' + self.github_common["token"], }

    def run(self):
        session = self.create_model()
        logger.info(f"Database model has been created successfully")
        pr_max_id = self.get_max_pr_id(session)
        logger.info(f"Max PullRequest Id is {pr_max_id}")
        pr_max_updated_time = self.get_max_pr_updated(session)
        logger.info(f"Max PullRequest Updated Time is {pr_max_id}")
        pr_end_cursor = False
        pr_has_next_page = True
        while pr_has_next_page:
            prs_params = self.get_pull_requests_params(pr_end_cursor)
            prs_query = self.read_query_from_template(
                os.path.join(PACKAGE_ROOT_DIR, self.github_common["graphql_prs_path"]),
                prs_params)
            result = self.send_http_request(prs_query)
            pr_has_next_page = result["data"]["repository"]["pullRequests"]["pageInfo"]["hasNextPage"]
            pr_end_cursor = result["data"]["repository"]["pullRequests"]["pageInfo"]["endCursor"]
            result_gen = (x for x in result["data"]["repository"]["pullRequests"]["nodes"]
                          if x["number"] > pr_max_id
                          or utc_to_local(x["updatedAt"]) > pr_max_updated_time)
            for node in result_gen:
                logger.info(f"Start processing Pull Request number: {node['number']}")
                pr = PullRequests(node["number"],
                                  node["title"],
                                  node["state"],
                                  node["merged"],
                                  node["createdAt"],
                                  node["updatedAt"],
                                  node["mergedAt"]
                                  )
                pull_files_all = []
                if node["files"] is not None:
                    file_has_next_page = node["files"]["pageInfo"]["hasNextPage"]
                    file_end_cursor = node["files"]["pageInfo"]["endCursor"]
                    for edge in node["files"]["edges"]:
                        pull_files_all.append(PullRequestsFiles(node["number"], edge["node"]["path"]))
                    if file_has_next_page:
                        while file_has_next_page:
                            file_has_next_page, file_end_cursor, pull_files = \
                                self.query_pull(node["number"], file_end_cursor)
                            pull_files_all.extend(pull_files)
                    logger.info(f"Pull Request number: {node['number']}, Files count: {len(pull_files_all)}")
                if node["number"] > pr_max_id:
                    session.add(pr)
                    if node["files"] is not None:
                        session.add_all(pull_files_all)
                if utc_to_local(node["updatedAt"]) > pr_max_updated_time and node["number"] <= pr_max_id:
                    session.merge(pr)
                    if node["files"] is not None:
                        for pull in pull_files_all:
                            session.merge(pull)
            session.commit()
        session.close()

    def create_model(self):
        Base.metadata.create_all(self.engine, checkfirst=True)
        Session = sessionmaker()
        Session.configure(bind=self.engine)
        return Session()

    def read_query_from_template(self, template_path, params):
        with open(template_path) as f:
            graphql = f.read()
        query, bind_params = self.jinja_format.prepare_query(graphql, params)
        return query

    def get_pull_requests_params(self, pr_end_cursor):
        final_pr_cursor = "" if not pr_end_cursor else ', after: "{}"'.format(pr_end_cursor)
        return {
            'repo_owner': self.github_common["repo_owner"],
            'repo_name': self.github_common["repo_name"],
            'items_per_page': self.github_common["items_per_page"],
            'pr_cursor': final_pr_cursor
        }

    def query_pull(self, pull_request_number, file_end_cursor):
        pr_params = {
            'repo_owner': self.github_common["repo_owner"],
            'repo_name': self.github_common["repo_name"],
            'items_per_page': self.github_common["items_per_page"],
            'file_cursor': file_end_cursor,
            'pr_number': pull_request_number
        }
        pr_query = self.read_query_from_template(
            os.path.join(PACKAGE_ROOT_DIR, self.github_common["graphql_pr_path"]),
            pr_params)
        result = self.send_http_request(pr_query)
        pull_files = []
        for edge in result["data"]["repository"]["pullRequest"]["files"]["edges"]:
            pull_files.append(PullRequestsFiles(pull_request_number, edge["node"]["path"]))
        return result["data"]["repository"]["pullRequest"]["files"]["pageInfo"]["hasNextPage"], \
               result["data"]["repository"]["pullRequest"]["files"]["pageInfo"]["endCursor"], \
               pull_files

    def send_http_request(self, query):
        try:
            logger.info(f"Request query from: {self.github_common['graphql_api_url']}")
            request = requests.post(self.github_common["graphql_api_url"],
                                    json={'query': query},
                                    headers=self.headers)
            request.raise_for_status()
            if request.status_code == 200:
                return request.json()
        except requests.exceptions.HTTPError as errh:
            logger.error(f"HTTP Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            logger.error(f"Connection Error: {errc}")
        except requests.exceptions.Timeout as errt:
            logger.error(f"Timeout Error: {errt}")
        except requests.exceptions.TooManyRedirects as errr:
            logger.error(f"TooManyRedirects: {errr}")
        except requests.exceptions.RequestException as err:
            logger.error(f"Request Error: {err}")

    def get_max_pr_id(self, session):
        pr_max_id = session.query(func.max(PullRequests.id)).scalar()
        return pr_max_id if pr_max_id is not None else 0

    def get_max_pr_updated(self, session):
        pr_max_updated_time = session.query(func.max(PullRequests.updated_time)).scalar()
        return pr_max_updated_time if pr_max_updated_time is not None \
            else dt.datetime.strptime("1900-01-01", '%Y-%m-%d')

    def get_max_pr_merge_time(self, session):
        return session.query(func.max(func.datediff('second', PullRequests.created_time, PullRequests.merged_time)),
                             func.avg(func.datediff('second', PullRequests.created_time, PullRequests.merged_time)),
                             func.min(func.datediff('second', PullRequests.created_time, PullRequests.merged_time))) \
            .filter(PullRequests.state == "MERGED").first()

    def get_most_often_changed_files(self, session):
        return session.query(PullRequestsFiles.file_name, func.count(PullRequestsFiles.pull_request_id))\
            .group_by(PullRequestsFiles.file_name)\
            .order_by(func.count(PullRequestsFiles.pull_request_id).desc())\
            .limit(3).all()
