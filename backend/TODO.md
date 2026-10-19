# TODO - Class-based APIView refactor

## Plan
- [x] Inspect existing function-based views in:
  - [x] backend/agents/views.py
  - [x] backend/mcp/views.py
  - [x] backend/monitoring/views.py

- [x] Refactor each @api_view function into DRF class-based views (APIView) with `get`/`post` methods.

- [x] Update URL confs to point to the new `.as_view()` endpoints for `agents`.

- [x] Refactor function-based views in `backend/mcp/views.py` into DRF `APIView` classes.
- [x] Update `backend/mcp/urls.py` to use `.as_view()`.

- [x] Refactor function-based views in `backend/monitoring/views.py` into DRF `APIView` classes.
- [x] Update `backend/monitoring/urls.py` to use `.as_view()`.

- [x] Remove unused `@api_view` decorators/imports where applicable.
- [ ] Run Django checks/tests (e.g., `python manage.py check`).


