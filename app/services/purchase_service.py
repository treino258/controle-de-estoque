from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from sqlite3 import IntegrityError
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database.seed import DEFAULT_TENANT_ID
from app.models import Expense, Product, Sale, StockLot, StockMovement
from app.models.enums import ProductType
from app.models.recipes import RecipeItem