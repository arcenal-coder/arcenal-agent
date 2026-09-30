"""Contrats et orchestration interne d’ARCenal Agent."""

from .catalog import default_agents
from .context import ContextBuilder, GlobalAgentPolicy
from .manager import AgentManager
from .knowledge_index import KnowledgeIndexer, KnowledgeIndexRepository
from .knowledge_metrics import KnowledgeMetricsRepository
from .knowledge_models import (
    ConfidentialityLevel,
    ContextBudget,
    ContextPlan,
    DocumentStatus,
    KnowledgeIndexStatus,
    KnowledgeFilters,
    SourceCitation,
    SourceType,
)
from .knowledge_search import KnowledgeRetriever
from .knowledge_source import MarkdownKnowledgeSource
from .knowledge_runtime import create_retriever, index_status, rebuild_index
from .document_extraction import (
    DocumentExtractionError,
    DocumentExtractionUnavailable,
    extract_attachment_text,
)
from .silverbullet import (
    HttpxSilverBulletTransport,
    SilverBulletAuthenticationError,
    SilverBulletError,
    SilverBulletProtocolError,
    SilverBulletResponse,
    SilverBulletSettings,
    SilverBulletStateRepository,
    SilverBulletSyncResult,
    SilverBulletSynchronizer,
)
from .models import (
    AgentDefinition,
    AgentQueryResponse,
    AgentUpdate,
    ApplicationIdentity,
    AutonomyLevel,
    EffectiveContext,
    EngineOutput,
    InstructionBlock,
    ModelPolicy,
    RequestIdentity,
)
from .repository import AgentRepository
from .service import ArcCore

__all__ = [
    "AgentDefinition",
    "AgentManager",
    "AgentQueryResponse",
    "AgentRepository",
    "AgentUpdate",
    "ApplicationIdentity",
    "ArcCore",
    "AutonomyLevel",
    "ContextBuilder",
    "ConfidentialityLevel",
    "ContextBudget",
    "ContextPlan",
    "DocumentStatus",
    "DocumentExtractionError",
    "DocumentExtractionUnavailable",
    "EffectiveContext",
    "EngineOutput",
    "GlobalAgentPolicy",
    "InstructionBlock",
    "KnowledgeIndexer",
    "KnowledgeIndexRepository",
    "KnowledgeIndexStatus",
    "KnowledgeFilters",
    "KnowledgeMetricsRepository",
    "KnowledgeRetriever",
    "MarkdownKnowledgeSource",
    "ModelPolicy",
    "RequestIdentity",
    "SourceCitation",
    "SourceType",
    "HttpxSilverBulletTransport",
    "SilverBulletAuthenticationError",
    "SilverBulletError",
    "SilverBulletProtocolError",
    "SilverBulletResponse",
    "SilverBulletSettings",
    "SilverBulletStateRepository",
    "SilverBulletSyncResult",
    "SilverBulletSynchronizer",
    "default_agents",
    "create_retriever",
    "extract_attachment_text",
    "index_status",
    "rebuild_index",
]
