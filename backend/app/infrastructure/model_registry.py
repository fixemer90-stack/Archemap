"""Ensure SQLAlchemy metadata knows about ORM models used by worker/runtime paths."""

from __future__ import annotations

# Import model modules for side effects: table registration in Base.metadata.
from app.modules.astrotype_v2 import models as _astrotype_v2_models  # noqa: F401
from app.modules.profiles import models as _profiles_models  # noqa: F401
from app.modules.report_narratives import models as _report_narratives_models  # noqa: F401
from app.modules.reports import models as _reports_models  # noqa: F401
from app.modules.users import models as _users_models  # noqa: F401
