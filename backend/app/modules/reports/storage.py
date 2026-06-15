"""Legacy report artifact storage module.

PDF artifacts are no longer stored in S3/MinIO. Reports persist structured JSON in
Postgres (`reports.report_data` plus `report_narratives.content`) and render PDFs
on demand in the reports API.
"""

from __future__ import annotations
