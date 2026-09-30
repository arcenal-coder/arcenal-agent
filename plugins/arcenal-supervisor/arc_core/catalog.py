"""Définitions natives des agents fournis par ARCenal Agent."""

from .models import AgentDefinition, AutonomyLevel, InstructionBlock, ModelPolicy


def _arc_agent() -> AgentDefinition:
    return AgentDefinition(
        id="arc",
        name="ARC",
        description="Architecte et administrateur intelligent d’ARCenal Système.",
        role="system-architect",
        application="arcenal-system",
        system_instructions=(InstructionBlock(id="mission", content="Superviser ARCenal Système sans contourner les validations humaines ni les politiques YunoHost."),),
        permissions=("lda.history", "lda.read", "memory.read", "system.admin", "system.read", "tools.execute"),
        tools=("arcenal-supervisor",),
        knowledge_scopes=("company", "system", "technical"),
        model_policy=ModelPolicy(),
        autonomy_level=AutonomyLevel.APPROVAL_REQUIRED,
        metadata={"profile": "default", "color": "primary"},
    )


def _ats_agent() -> AgentDefinition:
    return AgentDefinition(
        id="ats",
        name="Agent ATS",
        description="Assistant spécialisé dans le recrutement et le suivi des candidatures.",
        role="recruitment",
        application="arcenal-ats",
        system_instructions=(InstructionBlock(id="mission", content="Assister le recrutement uniquement dans le périmètre ATS autorisé et demander validation avant toute mutation."),),
        permissions=("ats.read", "lda.read"),
        tools=(),
        knowledge_scopes=("ats", "company", "recruitment"),
        model_policy=ModelPolicy(local_preferred=True),
        autonomy_level=AutonomyLevel.CONTROLLED,
        metadata={"profile": "ats", "color": "secondary"},
    )


def default_agents() -> tuple[AgentDefinition, ...]:
    return (_arc_agent(), _ats_agent())
