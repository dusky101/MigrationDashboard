"""
Analytics Module

Fleet-wide analytics and aggregation functions for the
Migration Intelligence Platform.
"""

from .fleet_analytics import (
    load_all_audits,
    get_fleet_metrics,
    get_hardware_distribution,
    get_software_distribution,
    get_storage_analytics,
    get_top_applications,
    get_compliance_summary,
    get_devices_needing_attention,
    export_fleet_summary_csv,
)

__all__ = [
    'load_all_audits',
    'get_fleet_metrics',
    'get_hardware_distribution',
    'get_software_distribution',
    'get_storage_analytics',
    'get_top_applications',
    'get_compliance_summary',
    'get_devices_needing_attention',
    'export_fleet_summary_csv',
]
