from sqlalchemy import Column, String, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Result(Base):
    __tablename__ = "results"
    
    id             = Column(Integer, primary_key=True, index=True)
    session_id     = Column(String, nullable=False)
    ci             = Column(String, nullable=False)
    run_id         = Column(String, nullable=False)
    branch         = Column(String, nullable=False)
    repository     = Column(String, nullable=False)
    workflow_id    = Column(String, nullable=False)
    workflow_name  = Column(String, nullable=False)
    commit_hash    = Column(String, nullable=False)
    approach       = Column(String, nullable=False)
    method         = Column(String, nullable=False)
    label          = Column(String, nullable=False)
    json_main      = Column(String, nullable=False)
    json_baseline  = Column(String, nullable=True)

    def __init__(
        self,
        session_id=None,
        ci=None,
        run_id=None,
        branch=None,
        repository=None,
        workflow_id=None,
        workflow_name=None,
        commit_hash=None,
        method=None,
        approach=None,
        label=None,
        json_main=None,
        json_baseline=None
    ):
        self.session_id = session_id
        self.ci = ci
        self.run_id = run_id
        self.branch = branch
        self.repository = repository
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.commit_hash = commit_hash
        self.method = method
        self.approach = approach
        self.label = label
        self.json_main = json_main or {}
        self.json_baseline = json_baseline

    def __repr__(self):
        return (
            f"<Result(id={self.id!r}, session_id={self.session_id!r}, ci={self.ci!r}, run_id={self.run_id!r}, "
            f"branch={self.branch!r}, repository={self.repository!r}, workflow_id={self.workflow_id!r}, "
            f"workflow_name={self.workflow_name!r}, commit_hash={self.commit_hash!r}, "
            f"method={self.method!r}, approach={self.approach!r}, label={self.label!r}, "
            f"json_main={self.json_main!r}, json_baseline={self.json_baseline!r})>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "ci": self.ci,
            "run_id": self.run_id,
            "branch": self.branch,
            "repository": self.repository,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "commit_hash": self.commit_hash,
            "method": self.method,
            "approach": self.approach,
            "label": self.label,
            "json_main": self.json_main,
            "json_baseline": self.json_baseline
        }
