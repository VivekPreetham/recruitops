from typing import TypedDict

class JobAnalysisState(TypedDict, total=False):
    job_id: str
    title: str
    description: str
    requirements: dict
    confirmed: dict
    confirmed_by: str