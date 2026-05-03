# Product Generation Guide

## Overview

The VibeFactory Product Generation system transforms user stories into complete, deployable products. This guide covers:

- How product generation works
- Running and customizing generated products
- Deploying to production
- Extending generated code
- Troubleshooting

## Architecture

### Multi-Layer Generation Pipeline

```
Rough Idea
    ↓
Orchestrator (Blind Critique Loop)
    ├─ BRD (Business Requirements)
    ├─ PRD (Product Requirements)
    ├─ TRD (Technical Requirements)
    └─ STORIES (User Stories)
        ↓
Product Generator
    ├─ StoryTranslator: Story → BackendSpec + FrontendSpec
    ├─ BackendGenerator: BackendSpec → FastAPI Code
    ├─ FrontendGenerator: FrontendSpec → Vanilla JS Code
    └─ ProductAssemblyManager: Assemble → Complete Product
        ↓
Deployable Product
    ├─ Backend API (FastAPI)
    ├─ Frontend (Vanilla JS + HTML/CSS)
    ├─ Database (SQLite)
    ├─ Docker Compose Setup
    └─ Documentation
```

### Story Translation

Each story is automatically analyzed and translated into:

**BackendSpec:**
- API Endpoints (CRUD operations)
- Database Models (SQLAlchemy ORM)
- Middleware (CORS, error handling, logging)
- Dependencies (pip packages)

**FrontendSpec:**
- UI Pages (HTML templates)
- Components (JavaScript + CSS)
- API Integration (fetch calls)
- Navigation & Routing

## Generated Product Structure

```
products/
└── {project_id}/
    ├── docker-compose.yml           # Orchestration file
    ├── start.sh                     # Launcher script
    ├── README.md                    # Quick start guide
    ├── .gitignore                   # Git configuration
    ├── app/                         # Backend (FastAPI)
    │   ├── main.py                  # FastAPI app
    │   ├── models.py                # SQLAlchemy models
    │   ├── database.py              # Database setup
    │   ├── routes.py                # Endpoint handlers
    │   └── __init__.py
    ├── www/                         # Frontend (Vanilla JS)
    │   ├── index.html               # Main page
    │   ├── dashboard.html           # Story dashboard (auto-generated)
    │   ├── api-explorer.html        # API testing tool (auto-generated)
    │   ├── styles.css               # Global styles with dark/light mode
    │   ├── api.js                   # API client helper
    │   ├── nav.js                   # Navigation system
    │   └── pages/                   # Generated pages
    │       ├── {story_name}.html
    │       └── {story_name}.js
    ├── tests/                       # Backend tests
    │   ├── conftest.py              # Pytest configuration
    │   ├── test_routes.py           # Route tests
    │   └── __init__.py
    ├── requirements.txt             # Python dependencies
    └── .env.example                 # Environment template
```

## Quick Start

### 1. Start the Product

```bash
# Navigate to generated product
cd products/{project_id}

# Make launcher executable
chmod +x start.sh

# Start services with docker-compose
./start.sh
# OR manually:
docker-compose up --build
```

### 2. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **API Explorer**: http://localhost:3000/api-explorer.html
- **Dashboard**: http://localhost:3000/dashboard.html

### 3. Run Tests

```bash
# In the product directory
docker-compose exec api pytest tests/ -v
# OR locally:
pip install -r requirements.txt
pytest tests/ -v
```

## Backend Development

### Adding New Endpoints

Generated endpoints follow RESTful patterns:

```python
# In app/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, database

router = APIRouter()

@router.get("/items", tags=["items"])
async def list_items(skip: int = 0, limit: int = 10, 
                     db: Session = Depends(database.get_db)):
    """Get paginated list of items."""
    items = db.query(models.Item).offset(skip).limit(limit).all()
    return {"items": items, "total": len(items)}

@router.post("/items", status_code=201)
async def create_item(item_data: dict, 
                      db: Session = Depends(database.get_db)):
    """Create new item."""
    db_item = models.Item(**item_data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
```

### Adding Database Models

```python
# In app/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Environment Variables

Create `.env` file for configuration:

```bash
# Database
DATABASE_URL=sqlite:///./app.db
# or for production:
# DATABASE_URL=postgresql://user:password@localhost/dbname

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]

# Logging
LOG_LEVEL=INFO
```

## Frontend Development

### Adding New Pages

Generated pages use vanilla JavaScript with structured patterns:

```html
<!-- In www/pages/tasks.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Tasks</title>
    <link rel="stylesheet" href="/styles.css">
    <link rel="stylesheet" href="/pages/tasks.css">
</head>
<body>
    <nav id="navbar"></nav>
    <main id="app-content">
        <div class="page-container">
            <h1>Tasks</h1>
            <button onclick="openCreateTaskModal()">Create Task</button>
            <div id="tasks-container"></div>
        </div>
    </main>
    
    <script src="/api.js"></script>
    <script src="/nav.js"></script>
    <script src="/pages/tasks.js"></script>
</body>
</html>
```

```javascript
// In www/pages/tasks.js
async function initTasksPage() {
    try {
        const response = await fetchAPI('/tasks');
        renderTasks(response.items);
    } catch (error) {
        showError(error.message);
    }
}

function renderTasks(tasks) {
    const container = document.getElementById('tasks-container');
    container.innerHTML = tasks.map(task => `
        <div class="task-card">
            <h3>${task.title}</h3>
            <p>${task.description}</p>
            <button onclick="editTask(${task.id})">Edit</button>
            <button onclick="deleteTask(${task.id})">Delete</button>
        </div>
    `).join('');
}

async function deleteTask(taskId) {
    if (!confirm('Delete this task?')) return;
    
    try {
        await fetchAPI(`/tasks/${taskId}`, { method: 'DELETE' });
        initTasksPage(); // Refresh
    } catch (error) {
        showError(error.message);
    }
}

document.addEventListener('DOMContentLoaded', initTasksPage);
```

### API Integration

The `fetchAPI` helper handles authentication and error handling:

```javascript
// Basic GET request
const data = await fetchAPI('/items');

// POST with body
const response = await fetchAPI('/items', {
    method: 'POST',
    body: { title: 'New Item', description: 'Description' }
});

// With authentication token (auto-included)
const response = await fetchAPI('/protected-endpoint');
// Token is read from localStorage automatically
```

### Theming

Generated CSS uses CSS variables for easy theming:

```css
/* Light mode (default) */
:root {
    --bg-primary: #ffffff;
    --bg-secondary: #f5f5f5;
    --text-primary: #000000;
    --text-secondary: #666666;
    --border-color: #cccccc;
    --accent-color: #2196F3;
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
    :root {
        --bg-primary: #1e1e1e;
        --bg-secondary: #2d2d2d;
        --text-primary: #ffffff;
        --text-secondary: #aaaaaa;
        --border-color: #444444;
        --accent-color: #64B5F6;
    }
}
```

## Production Deployment

### Docker Deployment

Products include `docker-compose.yml` for easy deployment:

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./app.db
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./app.db:/app/app.db

  web:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./www:/usr/share/nginx/html
```

### Deployment Steps

1. **Set Environment Variables**
   ```bash
   export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   export DATABASE_URL=postgresql://user:password@db:5432/myapp
   ```

2. **Build and Deploy**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Run Migrations** (if using PostgreSQL)
   ```bash
   docker-compose exec api alembic upgrade head
   ```

4. **Verify Health**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:3000/
   ```

## Troubleshooting

### Frontend Not Loading Pages

**Issue**: Pages not appearing in navigation or 404 errors

**Solutions**:
1. Check page is registered in `nav.js`
2. Verify HTML file exists in `www/pages/`
3. Check browser console for JavaScript errors
4. Verify API endpoint is accessible

### API Endpoints Returning 500 Errors

**Issue**: Backend errors when calling endpoints

**Solutions**:
1. Check container logs: `docker-compose logs api`
2. Verify database migrations ran
3. Check `.env` file is properly set
4. Review error in FastAPI docs: http://localhost:8000/docs

### Database Connection Issues

**Issue**: SQLite or PostgreSQL connection failures

**Solutions**:
1. For SQLite: Ensure `./app.db` is writable
2. For PostgreSQL: Verify connection string in `.env`
3. Check database is running: `docker-compose ps`
4. Restart services: `docker-compose restart`

### Port Conflicts

**Issue**: Ports 3000 or 8000 already in use

**Solutions**:
1. Change ports in `docker-compose.yml`
2. Kill existing processes:
   ```bash
   lsof -i :3000  # Find process on port 3000
   kill -9 <PID>   # Kill it
   ```

## Customization Examples

### Add Authentication

```python
# In app/models.py
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

# In app/routes.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])

@router.post("/auth/register")
async def register(email: str, password: str, db: Session):
    hashed = pwd_context.hash(password)
    user = User(email=email, password_hash=hashed)
    db.add(user)
    db.commit()
    return {"user_id": user.id}
```

### Add Search/Filtering

```python
@router.get("/items/search")
async def search_items(
    q: str = None,
    status: str = None,
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Item)
    
    if q:
        query = query.filter(models.Item.title.ilike(f"%{q}%"))
    
    if status:
        query = query.filter(models.Item.status == status)
    
    return query.all()
```

### Add Pagination

```javascript
// In frontend
let currentPage = 1;
const pageSize = 10;

async function loadItems(page = 1) {
    const skip = (page - 1) * pageSize;
    const data = await fetchAPI(`/items?skip=${skip}&limit=${pageSize}`);
    renderItems(data.items);
    updatePagination(data.total, page);
}

function updatePagination(total, currentPage) {
    const pages = Math.ceil(total / pageSize);
    const pagination = document.getElementById('pagination');
    
    pagination.innerHTML = Array.from({ length: pages }, (_, i) => `
        <button onclick="loadItems(${i + 1})" 
                class="${i + 1 === currentPage ? 'active' : ''}">
            ${i + 1}
        </button>
    `).join('');
}
```

## Performance Optimization

### Backend

```python
# Add database indexes
class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)  # Index for search
    created_at = Column(DateTime, index=True)

# Use pagination in queries
@router.get("/items")
async def list_items(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(database.get_db)
):
    return db.query(models.Item).offset(skip).limit(limit).all()
```

### Frontend

```javascript
// Debounce search input
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

const debouncedSearch = debounce(async (query) => {
    const results = await fetchAPI(`/items/search?q=${query}`);
    renderResults(results);
}, 300);

document.getElementById('search').addEventListener('input', (e) => {
    debouncedSearch(e.target.value);
});
```

## Next Steps

1. **Extend Generated Code**: Add business logic to generated endpoints
2. **Add Tests**: Write additional tests for custom functionality
3. **Deploy**: Use docker-compose for local deployment, cloud platforms for production
4. **Monitor**: Set up logging and monitoring in production
5. **Iterate**: Make improvements and regenerate as needed

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review generated `README.md` in product
3. Check FastAPI docs: https://fastapi.tiangolo.com
4. Review generated code and comments

---

**Generated by VibeFactory Product Generator**
This guide is customized to your specific product structure.
