"""Mixins reutilizáveis para multi-tenant e auditoria."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, func


class TenantMixin:
    """Prepara SaaS: todas as entidades pertencem a um tenant."""

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        default=1,
        index=True,
    )


class TimestampMixin:
    """Rastreio de criação/atualização para auditoria e suporte."""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )
