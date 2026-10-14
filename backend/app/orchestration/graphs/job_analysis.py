from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from app.agents.job_analysis import analyze_job
from app.orchestration.retry import LLM_RETRY
from app.orchestration.state import JobAnalysisState
from app.schemas.job_requirements import JobRequirements


def build_job_analysis_graph(checkpointer, llm: BaseChatModel | None = None):
    def analyze_node(state: JobAnalysisState) -> dict:
        result=analyze_job(state["title"], state["description"], llm=llm)
        return {"requirements": result.model_dump()}

    def review_node(state: JobAnalysisState) -> dict:
        decision = interrupt(
            {"type": "requirements_review", "draft": state["requirements"]}
        )
        confirmed = JobRequirements.model_validate(decision["requirements"])
        return {"confirmed": confirmed.model_dump(), "confirmed_by": decision["confirmed_by"]}

    builder = StateGraph(JobAnalysisState)
    builder.add_node("analyze", analyze_node, retry_policy=LLM_RETRY)
    builder.add_node("review", review_node)
    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "review")
    builder.add_edge("review", END)
    return builder.compile(checkpointer=checkpointer)