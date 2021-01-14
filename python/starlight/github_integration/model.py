from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import func
import logging

logger = logging.getLogger("startlight")

Base = declarative_base()

class PullRequests(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, autoincrement=False, primary_key=True)
    name = Column(String, nullable=False)
    state = Column(String(6), nullable=False)
    is_merged = Column(Boolean)
    created_time = Column(DateTime, nullable=False)
    updated_time = Column(DateTime, nullable=False)
    merged_time = Column(DateTime)
    files = relationship("PullRequestsFiles")

    def __init__(self, id, name, state, is_merged, created_time, updated_time,
                 merged_time):
        self.id = id
        self.name = name
        self.state = state
        self.is_merged = is_merged
        self.created_time = created_time
        self.updated_time = updated_time
        self.merged_time = merged_time


class PullRequestsFiles(Base):
    __tablename__ = "pull_requests_files"

    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), primary_key=True)
    file_name = Column(String(4096), primary_key=True)

    def __init__(self, pull_request_id, file_name):
        self.pull_request_id = pull_request_id
        self.file_name = file_name

    @classmethod
    def get(cls):
        return cls.query(PullRequestsFiles.file_name, func.count(PullRequestsFiles.pull_request_id)) \
            .group_by(PullRequestsFiles.file_name) \
            .order_by(func.count(PullRequestsFiles.pull_request_id).desc()) \
            .limit(3).all()