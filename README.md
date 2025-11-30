# CMMS - Computerized Maintenance Management System

Enterprise-grade CMMS built with modern architecture patterns inspired by industry leaders like IBM Maximo, SAP PM, FIIX, MaintainX, UpKeep, eMaint, and Limble.

## Features

### Core Functionality
- **Asset Management** - Hierarchical asset registry with specifications, meters, and documents
- **Work Order Management** - Full lifecycle with configurable status workflows
- **Preventive Maintenance** - Time-based, meter-based, and condition-based scheduling
- **Inventory Management** - Parts, storerooms, stock levels, and purchase orders
- **Reporting & Analytics** - Dashboard metrics, MTBF/MTTR, PM compliance

### Technical Highlights
- Multi-tenant architecture with row-level security
- JWT + API key authentication
- Background PM scheduling engine
- Real-time work order status tracking
- Low stock alerts and reorder management
- Responsive web interface

## Architecture

```
CMMS/
├── backend/               # FastAPI Python backend
│   ├── app/
│   │   ├── api/          # REST API endpoints
│   │   ├── core/         # Configuration, security, database
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic validation schemas
│   │   └── services/     # Business logic services
│   └── requirements.txt
├── frontend/              # React TypeScript frontend
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Page components
│   │   ├── lib/          # API client and utilities
│   │   └── stores/       # Zustand state management
│   └── package.json
└── README.md
```

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with asyncpg
- **ORM**: SQLAlchemy 2.0 (async)
- **Authentication**: JWT + API keys
- **Scheduling**: APScheduler

### Frontend
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS
- **State**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Charts**: Recharts
- **Build**: Vite

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

### Backend Setup

1. Create and activate a virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create the database:
```sql
CREATE DATABASE cmms;
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. Run the server:
```bash
python -m uvicorn app.main:app --reload
```

6. Seed demo data (optional):
```bash
python -m app.services.seed_data
```

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Run development server:
```bash
npm run dev
```

3. Open http://localhost:3000

### Demo Credentials
- **Admin**: admin@demo.com / admin123
- **Technician**: tech@demo.com / tech123

## API Documentation

Once the backend is running, access:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

## Data Models

### Core Entities
- **Organization** - Multi-tenant isolation
- **User** - Authentication and authorization
- **Location** - Hierarchical facility structure
- **Asset** - Equipment with specifications and meters
- **WorkOrder** - Maintenance tasks with status workflow
- **PreventiveMaintenance** - Scheduled maintenance triggers
- **Part** - Inventory items
- **PurchaseOrder** - Procurement management

### Work Order Status Flow
```
DRAFT → WAITING_APPROVAL → APPROVED → SCHEDULED → IN_PROGRESS → COMPLETED → CLOSED
                                                      ↓
                                                   ON_HOLD
```

### PM Trigger Types
- **TIME** - Calendar-based (every X days/weeks/months)
- **METER** - Usage-based (every X hours/miles)
- **CONDITION** - Threshold-based (sensor triggers)
- **TIME_OR_METER** - First condition wins
- **TIME_AND_METER** - Both conditions required

## Key Endpoints

### Authentication
- `POST /api/v1/auth/login` - Get JWT tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Current user info

### Assets
- `GET /api/v1/assets` - List assets
- `POST /api/v1/assets` - Create asset
- `GET /api/v1/assets/{id}` - Get asset details
- `GET /api/v1/assets/barcode/{barcode}` - Find by barcode

### Work Orders
- `GET /api/v1/work-orders` - List work orders
- `POST /api/v1/work-orders` - Create work order
- `PUT /api/v1/work-orders/{id}/status` - Update status
- `POST /api/v1/work-orders/{id}/labor` - Add labor time
- `POST /api/v1/work-orders/{id}/materials` - Add materials

### Preventive Maintenance
- `GET /api/v1/pm` - List PM schedules
- `GET /api/v1/pm/due` - Get due PMs
- `POST /api/v1/pm/{id}/generate-wo` - Generate work order

### Inventory
- `GET /api/v1/inventory/parts` - List parts
- `GET /api/v1/inventory/parts/low-stock` - Low stock alerts
- `POST /api/v1/inventory/stock/adjust` - Adjust stock

### Reports
- `GET /api/v1/reports/dashboard` - Dashboard metrics
- `GET /api/v1/reports/work-orders/summary` - WO statistics
- `GET /api/v1/reports/pm/compliance` - PM compliance
- `GET /api/v1/reports/mtbf-mttr` - Reliability metrics

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql+asyncpg://... |
| SECRET_KEY | JWT signing key | (generate secure key) |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiration | 30 |
| CORS_ORIGINS | Allowed origins | ["http://localhost:3000"] |

## License

MIT License
