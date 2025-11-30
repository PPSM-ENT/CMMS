# Copilot Instructions - CMMS

## Architecture Overview

**CMMS** is a multi-tenant Computerized Maintenance Management System with a **FastAPI backend** (Python 3.11+) and **React/TypeScript frontend**.

- **Backend**: `backend/app/` - Layered architecture with API routes → Services → Models → Database
- **Frontend**: `frontend/src/` - React pages with Zustand state management + TanStack Query for API calls
- **Database**: PostgreSQL with SQLAlchemy 2.0 async ORM + support for SQLite in dev

### Service Boundaries

- **Multi-tenancy**: All data scoped by `organization_id` via `TenantMixin`
- **Authentication**: JWT + API keys with role-based access (see `app/core/security.py`)
- **Background Jobs**: PM scheduler runs in app lifespan as async task in `app/services/pm_scheduler.py`
- **Audit Trail**: `AuditMixin` timestamps all records; `AuditLog` model tracks entity changes

## Key Patterns

### Backend Patterns

**Models** (`backend/app/models/`):
- Inherit from `Base`, `AuditMixin`, `TenantMixin` as needed
- Use `Mapped` type hints for SQLAlchemy 2.0 annotations
- Enums (e.g., `WorkOrderStatus`, `PMTriggerType`) drive workflow logic
- Example: `WorkOrder` with status transition rules in endpoint validation

**Endpoints** (`backend/app/api/v1/endpoints/`):
- CRUD operations + domain-specific actions (e.g., `PUT /work-orders/{id}/status`)
- Always enforce `organization_id == current_user.organization_id` for tenant isolation
- Status transitions validated against `STATUS_TRANSITIONS` dict (see `work_orders.py`)
- Pagination via query params; list endpoints filter by org

**Services** (`backend/app/services/`):
- Encapsulate complex business logic (PM scheduling, work order workflows)
- Use injected `async_session_maker` for background tasks
- Return domain objects or schemas, not raw DB models

**Schemas** (`backend/app/schemas/`):
- Pydantic v2 models for request/response validation
- Separate `Create`, `Update`, `Response` schemas
- Use `ConfigDict(from_attributes=True)` for ORM model conversion

### Frontend Patterns

**State Management** (`frontend/src/stores/authStore.ts`):
- Zustand with `persist` middleware for auth tokens
- `useAuthStore.getState()` in API interceptors
- Manual cleanup on 401: redirect to login

**API Client** (`frontend/src/lib/api.ts`):
- Axios instance with request/response interceptors
- All endpoints wrapped in named async functions (e.g., `getWorkOrders()`, `updateWorkOrderStatus()`)
- Form data for login: `OAuth2PasswordRequestForm` compatibility

**Pages & Components**:
- Pages use React Query (`useQuery`, `useMutation`) for data fetching
- Forms with `react-hook-form` + custom validation
- Tailwind + Lucide icons for UI
- Status updates use `updateWorkOrderStatus({ status, reason, completion_notes, ... })` schema

## Critical Workflows

### Work Order Lifecycle

**Status Flow**: `DRAFT` → `WAITING_APPROVAL` → `APPROVED` → `SCHEDULED` → `IN_PROGRESS` → `COMPLETED` → `CLOSED`
- Allowed transitions defined in `STATUS_TRANSITIONS` dict (not all states connect)
- `ON_HOLD` branch possible from `IN_PROGRESS`
- Endpoint validates new status against current status before updating

**Related Transactions**:
- Add labor: `POST /work-orders/{id}/labor` → `LaborTransaction`
- Add materials: `POST /work-orders/{id}/materials` → `MaterialTransaction`
- Add tasks: `POST /work-orders/{id}/tasks` → `WorkOrderTask`
- Comments tracked in `WorkOrderComment`

### PM Scheduling

**Triggers** (`app/models/preventive_maintenance.py`):
- `TIME`: calendar intervals (days/weeks/months)
- `METER`: usage-based (every X hours/miles)
- `CONDITION`: threshold sensors
- `TIME_OR_METER` / `TIME_AND_METER`: combined logic

**Generation**:
- `PMScheduler.process_due_pms()` runs every N minutes (async in app lifespan)
- Checks `PreventiveMaintenance.next_due_date` against today + lead time window
- Auto-generates `WorkOrder` with PM-linked tasks from `JobPlan`
- Updates `next_due_date` based on trigger type

### Inventory & Parts

**Stock Tracking**:
- `Part` (master) → `StockLevel` (per storeroom)
- Low stock alerts trigger at reorder point
- `PurchaseOrder` → `POLineItem` → receive workflow adjusts stock

**API Pattern**: 
- GET `/inventory/parts/low-stock` for alerts
- POST `/inventory/purchase-orders` creates PO
- POST `/inventory/purchase-orders/{id}/receive` marks received lines + updates `StockLevel`

## Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
# Configure .env or DATABASE_URL env var
python -m uvicorn app.main:app --reload
# Optional: python -m app.services.seed_data  (demo data)
```

### Frontend
```bash
cd frontend
npm install
npm run dev  # Vite dev server on http://localhost:3000 or 5173
```

### Database
- **PostgreSQL** (production): `postgresql+asyncpg://user:pass@localhost/cmms`
- **SQLite** (dev): `sqlite+aiosqlite:///cmms.db` (auto-initialized)

## Important Files & Conventions

| File | Purpose |
|------|---------|
| `backend/app/core/config.py` | Settings via `get_settings()`; env vars in `.env` |
| `backend/app/core/security.py` | JWT/API key creation, password hashing |
| `backend/app/api/deps.py` | FastAPI dependencies (`CurrentUser`, `DBSession`) |
| `backend/app/models/base.py` | Mixins: `TimestampMixin`, `AuditMixin`, `TenantMixin` |
| `frontend/src/lib/api.ts` | All API calls; edit here for new endpoints |
| `frontend/src/stores/authStore.ts` | Auth state; used by API interceptors |

## Testing Notes

- Backend: `pytest` with `pytest-asyncio` for async tests
- Frontend: TypeScript strict mode (`tsconfig.json`)
- No E2E tests currently; integration via manual testing
- Seed data: `app.services.seed_data` populates demo users/assets/work orders

## Common Tasks

**Add new endpoint**:
1. Create model in `backend/app/models/` if needed
2. Add schema in `backend/app/schemas/` (Create/Update/Response)
3. Add router in `backend/app/api/v1/endpoints/`
4. Add API client wrapper in `frontend/src/lib/api.ts`
5. Use in React page with `useQuery` / `useMutation`

**Add work order status**:
1. Update `WorkOrderStatus` enum in `backend/app/models/work_order.py`
2. Update `STATUS_TRANSITIONS` dict in endpoint
3. Test transition paths; update UI status dropdown

**Handle multi-tenancy**:
- Always filter by `current_user.organization_id` in queries
- Use `where(Model.organization_id == org_id)` in SQLAlchemy
- Frontend inherits org from `useAuthStore((s) => s.user.organization_id)`
