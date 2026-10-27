"""Server-side authorization rules for Multy.

This module is deliberately framework-independent. Call it only with user,
membership and company records loaded and validated by trusted server code;
never pass role/tenant claims directly from request JSON.
"""

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class Principal:
    user_id: str
    firm_id: str
    role: str
    company_ids: FrozenSet[str]


@dataclass(frozen=True)
class Company:
    company_id: str
    firm_id: str


ROLES = frozenset({"firm_admin", "accountant", "read_only"})
READ_ACTIONS = frozenset({"view", "list_documents", "download_document", "view_report"})
WRITE_ACTIONS = frozenset({"create", "update", "delete", "validate_document", "request_document"})
ADMIN_ACTIONS = frozenset({"manage_members", "change_roles", "view_audit_log"})


def can_access_company(principal: Principal, company: Company) -> bool:
    """Return true only for a known role and an explicitly authorized tenant."""
    if principal.role not in ROLES or not principal.user_id:
        return False
    if not principal.firm_id or principal.firm_id != company.firm_id:
        return False
    if principal.role == "firm_admin":
        return True
    return company.company_id in principal.company_ids


def is_authorized(principal: Principal, company: Company, action: str) -> bool:
    """Authorize an action after tenant access has been established."""
    if not can_access_company(principal, company):
        return False
    if action in READ_ACTIONS:
        return True
    if action in ADMIN_ACTIONS:
        return principal.role == "firm_admin"
    if action in WRITE_ACTIONS:
        return principal.role in {"firm_admin", "accountant"}
    return False
