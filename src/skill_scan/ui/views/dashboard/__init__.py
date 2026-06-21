"""Dashboard widget package — self-contained cards for the SkillScan dashboard."""

from ._base import DashboardWidget
from ._widgets import (
    ActionItemsWidget,
    AIBomWidget,
    AiModuleMapWidget,
    AIUsageWidget,
    HeroMetricsWidget,
    IntegrationHealthWidget,
    LibraryCompositionWidget,
    QuickActionsWidget,
    RecentActivityWidget,
    ScanVelocityWidget,
    SecurityPostureWidget,
    SystemSetupWidget,
    TrustHealthWidget,
    UpdatesWidget,
)

# Ordered registry — defines default row layout and available widget list.
# Each inner list is one row; widgets within a row share available width equally.
REGISTRY: list[type[DashboardWidget]] = [
    HeroMetricsWidget,
    IntegrationHealthWidget,
    AiModuleMapWidget,
    SecurityPostureWidget,
    ActionItemsWidget,
    AIUsageWidget,
    UpdatesWidget,
    RecentActivityWidget,
    LibraryCompositionWidget,
    ScanVelocityWidget,
    AIBomWidget,
    TrustHealthWidget,
    SystemSetupWidget,
    QuickActionsWidget,
]

DEFAULT_LAYOUT: list[list[str]] = [
    ["hero_metrics"],
    ["integration_health"],
    ["ai_module_map"],
    ["security_posture", "action_items"],
    ["ai_usage", "updates"],
    ["recent_activity", "library_composition"],
    ["scan_velocity", "ai_bom", "trust_health"],
    ["system_setup"],
    ["quick_actions"],
]

__all__ = [
    "DashboardWidget",
    "REGISTRY",
    "DEFAULT_LAYOUT",
    "HeroMetricsWidget",
    "IntegrationHealthWidget",
    "AiModuleMapWidget",
    "SecurityPostureWidget",
    "ActionItemsWidget",
    "AIUsageWidget",
    "UpdatesWidget",
    "RecentActivityWidget",
    "LibraryCompositionWidget",
    "ScanVelocityWidget",
    "AIBomWidget",
    "TrustHealthWidget",
    "SystemSetupWidget",
    "QuickActionsWidget",
]
