import sys

from langgraph.types import Command

from app.orchestration.checkpointer import get_checkpointer
from app.orchestration.graphs.job_analysis import build_job_analysis_graph
from scripts.smoke_job_analysis import JD

THREAD_ID = "job:smoke:v1"
CONFIG = {"configurable": {"thread_id": THREAD_ID}}


def start(graph):
    graph.invoke(
        {"job_id": "smoke", "title": "AI Engineer", "description": JD},
        CONFIG,
    )
    snap = graph.get_state(CONFIG)
    print("paused at:", snap.next)  # ('review',) means waiting for a human
    print("AI draft:", snap.values["requirements"])


def resume(graph):
    snap = graph.get_state(CONFIG)
    if not snap.next:
        print("Nothing is paused. Run 'start' first.")
        return
    draft = snap.values["requirements"]
    draft["required_skills"].append("Git")  # pretend the recruiter edited the draft
    graph.invoke(
        Command(resume={"requirements": draft, "confirmed_by": "smoke-user"}),
        CONFIG,
    )
    final = graph.get_state(CONFIG)
    print("finished, next =", final.next)  # () means the workflow is done
    print("confirmed:", final.values["confirmed"])


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "start"
    graph = build_job_analysis_graph(get_checkpointer())
    {"start": start, "resume": resume}[action](graph)