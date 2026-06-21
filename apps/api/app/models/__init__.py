"""Import all ORM models so they register with the shared metadata."""

from app.core.base import Base  # noqa: F401
from app.models.ai import (  # noqa: F401
    AICitation,
    AIFeature,
    AIFeedback,
    AIJob,
    AIOutput,
    AIPromptTemplate,
    AIUsageLedger,
)
from app.models.analytics import (  # noqa: F401
    CatalogItem,
    KPIDefinition,
    ReportDefinition,
    ReportRun,
)
from app.models.documents import (  # noqa: F401
    Document,
    DocumentAccessGrant,
    DocumentChunk,
    DocumentText,
    DocumentVersion,
)
from app.models.funding import (  # noqa: F401
    EligibilityRule,
    FormTemplate,
    FundingCall,
    FundingProgram,
    FundingSource,
)
from app.models.identity import (  # noqa: F401
    AuditLog,
    Delegation,
    Organization,
    Role,
    RoleAssignment,
    Session,
    User,
)
from app.models.organization import OrganizationUnit, ResearchGroup  # noqa: F401
from app.models.outputs import (  # noqa: F401
    OutputAuthor,
    OutputIdentifier,
    PublicationVenue,
    ResearchOutput,
    Verification,
)
from app.models.projects import (  # noqa: F401
    ChangeRequest,
    Closure,
    FinanceTransaction,
    ProgressReport,
    Project,
    ProjectBaseline,
    ProjectMember,
    ProjectTask,
    Risk,
)
from app.models.proposals import (  # noqa: F401
    Deliverable,
    Milestone,
    Proposal,
    ProposalBudgetLine,
    ProposalTeamMember,
    ProposalVersion,
    Submission,
    WorkPackage,
)
from app.models.researchers import (  # noqa: F401
    ExpertiseTaxonomy,
    ResearcherExpertise,
    ResearcherIdentifier,
    ResearcherProfile,
)
from app.models.reviews import (  # noqa: F401
    ConflictDeclaration,
    Council,
    CouncilMeeting,
    CouncilMember,
    Decision,
    Review,
    ReviewAssignment,
    ReviewerProfile,
    ReviewScore,
    ReviewTemplate,
    Vote,
)
from app.models.workflow import (  # noqa: F401
    Approval,
    Comment,
    Notification,
    WorkflowInstance,
    WorkflowTask,
    WorkflowTemplate,
)

__all__ = ["Base"]
