"""
Location model for hierarchical location management.
"""
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin, TenantMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.asset import Asset


class Location(Base, AuditMixin, TenantMixin):
    """
    Location represents a physical location in the facility hierarchy.
    Supports hierarchical structure with parent-child relationships.
    Types: OPERATING (where assets work), STOREROOM (where parts are stored)
    """

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Hierarchy
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id"), nullable=True, index=True
    )
    hierarchy_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # e.g., "1/5/23"
    hierarchy_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Location type
    location_type: Mapped[str] = mapped_column(
        String(20), default="OPERATING", nullable=False
    )  # OPERATING, STOREROOM, REPAIR

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Address/coordinates for mapping
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Contact
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="locations")
    parent: Mapped[Optional["Location"]] = relationship(
        "Location", remote_side="Location.id", back_populates="children"
    )
    children: Mapped[List["Location"]] = relationship("Location", back_populates="parent")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="location")

    def __repr__(self) -> str:
        return f"<Location(id={self.id}, code='{self.code}', name='{self.name}')>"

    def update_hierarchy(self) -> None:
        """Update hierarchy path and level based on parent."""
        if self.parent:
            parent_path = self.parent.hierarchy_path or str(self.parent.id)
            self.hierarchy_path = f"{parent_path}/{self.id}"
            self.hierarchy_level = self.parent.hierarchy_level + 1
        else:
            self.hierarchy_path = str(self.id)
            self.hierarchy_level = 0
