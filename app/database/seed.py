"""Dados iniciais obrigatórios (tenant padrão)."""

from sqlalchemy.orm import Session

from app.models import Tenant

DEFAULT_TENANT_ID = 1
DEFAULT_TENANT_SLUG = "default"


def ensure_default_tenant(session: Session) -> Tenant:
    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    if tenant:
        return tenant

    tenant = Tenant(
        id=DEFAULT_TENANT_ID,
        nome="Cafeteria Principal",
        slug=DEFAULT_TENANT_SLUG,
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant
