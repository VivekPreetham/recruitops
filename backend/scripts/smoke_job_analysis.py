from app.agents.job_analysis import analyze_job

JD = """AI Engineer (Remote, India)
We are looking for a fresher or 0-2 years experience engineer.
You must know Python and have built RAG applications with LangChain.
Knowledge of LangGraph and agent frameworks is a plus.
Nice to have: n8n, Docker. B.Tech in CS or related field.
You will build LLM-powered features and evaluate model outputs."""

if __name__ == "__main__":
    result = analyze_job("AI Engineer", JD)
    print(result.model_dump_json(indent=2))