from typing import Literal

from pydantic import BaseModel, Field, field_validator

Seniority = Literal["intern", "junior", "mid", "senior", "lead", "principal", "unspecified"]


class JobRequirements(BaseModel):
    required_skills: list[str] | None = Field(
        default_factory=list,
        description="Skills or technologies the job description says are required or must-have.",
    )
    preferred_skills: list[str] | None = Field(
        default_factory=list,
        description="Skills described as preferred, nice-to-have, a plus, or bonus.",
    )
    min_years_experience: float | None = Field(
        default=None,
        description="Minimum years of experience explicitly required. Null if not stated.",
    )
    preferred_years_experience: float | None = Field(
        default=None,
        description="Preferred (not required) years of experience. Null if not stated.",
    )
    education_requirements: list[str] | None = Field(
        default_factory=list,
        description="Degrees, fields of study or certifications mentioned.",
    )
    responsibilities: list[str] | None = Field(
        default_factory=list,
        description="Main duties of the role, as short phrases.",
    )
    domain_knowledge: list[str] | None = Field(
        default_factory=list,
        description="Industry or domain knowledge needed (e.g. fintech, healthcare, NLP).",
    )
    seniority: Seniority = Field(
        default="unspecified",
        description="Seniority level of the role. Use 'unspecified' if unclear.",
    )
    location_requirements: str | None = Field(
        default=None,
        description="Location, remote/hybrid/onsite expectations. Null if not stated.",
    )
    other_constraints: list[str] | None = Field(
        default_factory=list,
        description="Anything else: visa, notice period, shift timings, travel, etc.",
    )

    @field_validator(
        "required_skills",
        "preferred_skills",
        "education_requirements",
        "responsibilities",
        "domain_knowledge",
        "other_constraints",
    )
    @classmethod
    def clean_lists(cls, v: list[str] | None) -> list[str]:
        seen, out = set(), []
        for item in v or []:
            item = item.strip()
            if item and item.lower() not in seen:
                seen.add(item.lower())
                out.append(item)
        return out