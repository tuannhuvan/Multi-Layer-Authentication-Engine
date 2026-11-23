# Ma trận Truy vết (Traceability Matrix — §4, §13.4)

| Business Rule | User Story | Acceptance Criteria | OpenAPI Operation | Acceptance Test | ADR / NFR |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `BR-031-01`, `BR-031-04` | `US-012` | `AC-012-01` | `POST /api/v1/grades/calculate` | `tests/acceptance/test_us012_grades.py::test_ac012_01_golden_calculation` | `ADR-001` |
| `BR-031-03` | `US-012` | `AC-012-02` | `PUT /api/v1/classes/{classId}/grades` | `tests/acceptance/test_us012_grades.py::test_ac012_02_anti_idor_unit_scope` | `ADR-001` |
| `BR-031-03` | `US-012` | `AC-012-03` | `POST /api/v1/grades/approvals/{approvalId}/sign` | `tests/acceptance/test_us012_grades.py::test_ac012_03_require_acr_s3_signature` | `ADR-001` |
| `BR-031-02` | `US-012` | `AC-012-04` | `POST /api/v1/grades/calculate` | `tests/acceptance/test_us012_grades.py::test_ac012_04_exempt_zero_weight` | `ADR-001` |
