# ============================================
# STEP 1: Create the root project directory
# ============================================
mkdir incident-platform
cd incident-platform

# ============================================
# STEP 2: Initialize Git
# ============================================
git init

# ============================================
# STEP 3: Create the full directory structure
# ============================================

# Services directories
mkdir -p services/alert-ingestion
mkdir -p services/incident-management
mkdir -p services/oncall-service
mkdir -p services/web-ui
mkdir -p services/notification-service

# Monitoring directories
mkdir -p monitoring/grafana-dashboards
mkdir -p monitoring/grafana-provisioning/dashboards
mkdir -p monitoring/grafana-provisioning/datasources

# Database init scripts
mkdir -p database

# ============================================
# STEP 4: Create empty placeholder files
# ============================================

# Root-level files
touch docker-compose.yml
touch .env
touch .gitignore
touch README.md

# Alert Ingestion Service files
touch services/alert-ingestion/main.py
touch services/alert-ingestion/requirements.txt
touch services/alert-ingestion/Dockerfile
touch services/alert-ingestion/.dockerignore

# Incident Management Service files
touch services/incident-management/main.py
touch services/incident-management/requirements.txt
touch services/incident-management/Dockerfile
touch services/incident-management/.dockerignore

# On-Call Service files (Person 2 will fill these)
touch services/oncall-service/main.py
touch services/oncall-service/requirements.txt
touch services/oncall-service/Dockerfile
touch services/oncall-service/.dockerignore

# Web UI placeholder (Person 3 will fill this)
touch services/web-ui/Dockerfile
touch services/web-ui/.dockerignore

# Notification Service placeholder (Person 3 optional)
touch services/notification-service/main.py
touch services/notification-service/requirements.txt
touch services/notification-service/Dockerfile
touch services/notification-service/.dockerignore

# Monitoring files
touch monitoring/prometheus.yml
touch monitoring/grafana-dashboards/incident-overview.json
touch monitoring/grafana-dashboards/sre-performance.json
touch monitoring/grafana-provisioning/dashboards/dashboards.yml
touch monitoring/grafana-provisioning/datasources/datasources.yml

# Database init
touch database/init.sql

# CI/CD pipeline
touch run-pipeline.sh
chmod +x run-pipeline.sh

# ============================================
# STEP 5: Populate .gitignore
# ============================================
cat > .gitignore << 'EOF'
# Environment variables (NEVER commit secrets)
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
venv/
.venv/

# Node (for Person 3)
node_modules/
npm-debug.log*

# Docker
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Coverage reports
htmlcov/
.coverage
coverage.xml
EOF

# ============================================
# STEP 6: Populate .env
# ============================================
cat > .env << 'EOF'
# Database
POSTGRES_USER=hackathon
POSTGRES_PASSWORD=hackathon2026
POSTGRES_DB=incident_platform
DATABASE_URL=postgresql://hackathon:hackathon2026@database:5432/incident_platform

# Service Ports
ALERT_INGESTION_PORT=8001
INCIDENT_MANAGEMENT_PORT=8002
ONCALL_SERVICE_PORT=8003
NOTIFICATION_SERVICE_PORT=8004
WEB_UI_PORT=8080

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
EOF

# ============================================
# STEP 7: Populate database/init.sql
# ============================================
cat > database/init.sql << 'EOF'
-- ============================================
-- INCIDENT PLATFORM DATABASE SCHEMA
-- ============================================

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical','high','medium','low')),
    message TEXT NOT NULL,
    labels JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL,
    incident_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    service VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical','high','medium','low')),
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open','acknowledged','in_progress','resolved')),
    assigned_to VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    mtta_seconds FLOAT,
    mttr_seconds FLOAT
);

-- Incident notes table
CREATE TABLE IF NOT EXISTS incident_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID REFERENCES incidents(id) ON DELETE CASCADE,
    author VARCHAR(255),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add foreign key for alerts -> incidents
ALTER TABLE alerts
    ADD CONSTRAINT fk_alerts_incident
    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE SET NULL;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_alerts_service_severity ON alerts(service, severity);
CREATE INDEX IF NOT EXISTS idx_alerts_incident_id ON alerts(incident_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_service ON incidents(service);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at);
CREATE INDEX IF NOT EXISTS idx_incident_notes_incident_id ON incident_notes(incident_id);
EOF

# ============================================
# STEP 8: Populate shared .dockerignore
# ============================================
for service in alert-ingestion incident-management oncall-service notification-service; do
cat > services/$service/.dockerignore << 'EOF'
__pycache__
*.py[cod]
*$py.class
.env
.git
.gitignore
venv
.venv
*.egg-info
dist
build
.coverage
htmlcov
tests/__pycache__
EOF
done

# ============================================
# STEP 9: Populate requirements.txt for YOUR services
# ============================================
for service in alert-ingestion incident-management; do
cat > services/$service/requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn==0.27.0
prometheus-client==0.19.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
pydantic==2.5.3
httpx==0.26.0
pytest==7.4.4
pytest-cov==4.1.0
pytest-asyncio==0.23.3
EOF
done

# ============================================
# STEP 10: Populate Dockerfiles for YOUR services
# ============================================
for service in alert-ingestion incident-management; do
    if [ "$service" = "alert-ingestion" ]; then
        PORT=8001
    else
        PORT=8002
    fi

cat > services/$service/Dockerfile << EOF
# ---- Stage 1: Build dependencies ----
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: Runtime ----
FROM python:3.11-slim
WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser --disabled-password --no-create-home appuser

# Copy dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:\$PATH

# Copy application code
COPY . .

# Switch to non-root user
USER appuser

EXPOSE $PORT

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
    CMD curl -f http://localhost:$PORT/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
EOF
done

# ============================================
# STEP 11: Populate docker-compose.yml
# ============================================
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # ---- DATABASE ----
  database:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - db-data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - incident-platform
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ---- ALERT INGESTION SERVICE ----
  alert-ingestion:
    build: ./services/alert-ingestion
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      INCIDENT_MANAGEMENT_URL: http://incident-management:8002
    depends_on:
      database:
        condition: service_healthy
    networks:
      - incident-platform
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ---- INCIDENT MANAGEMENT SERVICE ----
  incident-management:
    build: ./services/incident-management
    ports:
      - "8002:8002"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      ONCALL_SERVICE_URL: http://oncall-service:8003
      NOTIFICATION_SERVICE_URL: http://notification-service:8004
    depends_on:
      database:
        condition: service_healthy
    networks:
      - incident-platform
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ---- ON-CALL SERVICE (Person 2) ----
  oncall-service:
    build: ./services/oncall-service
    ports:
      - "8003:8003"
    environment:
      DATABASE_URL: ${DATABASE_URL}
    depends_on:
      database:
        condition: service_healthy
    networks:
      - incident-platform
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ---- NOTIFICATION SERVICE (Person 3 - Optional) ----
  notification-service:
    build: ./services/notification-service
    ports:
      - "8004:8004"
    networks:
      - incident-platform
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ---- WEB UI (Person 3) ----
  web-ui:
    build: ./services/web-ui
    ports:
      - "8080:8080"
    depends_on:
      - alert-ingestion
      - incident-management
      - oncall-service
    networks:
      - incident-platform
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ---- PROMETHEUS ----
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - incident-platform
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  # ---- GRAFANA ----
  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana-provisioning/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana-provisioning/datasources:/etc/grafana/provisioning/datasources
      - ./monitoring/grafana-dashboards:/var/lib/grafana/dashboards
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    networks:
      - incident-platform

volumes:
  db-data:
  prometheus-data:
  grafana-data:

networks:
  incident-platform:
    driver: bridge
EOF

# ============================================
# STEP 12: Populate Prometheus config
# ============================================
cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'alert-ingestion'
    static_configs:
      - targets: ['alert-ingestion:8001']
    metrics_path: /metrics

  - job_name: 'incident-management'
    static_configs:
      - targets: ['incident-management:8002']
    metrics_path: /metrics

  - job_name: 'oncall-service'
    static_configs:
      - targets: ['oncall-service:8003']
    metrics_path: /metrics

  - job_name: 'notification-service'
    static_configs:
      - targets: ['notification-service:8004']
    metrics_path: /metrics
EOF

# ============================================
# STEP 13: Populate Grafana provisioning
# ============================================
cat > monitoring/grafana-provisioning/datasources/datasources.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

cat > monitoring/grafana-provisioning/dashboards/dashboards.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: 'Incident Platform'
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
EOF

# ============================================
# STEP 14: Verify the structure
# ============================================
echo ""
echo "============================================"
echo "✅ PROJECT STRUCTURE CREATED SUCCESSFULLY!"
echo "============================================"
echo ""

# Print the tree (use find if 'tree' not installed)
if command -v tree &> /dev/null; then
    tree -a --dirsfirst -I '.git'
else
    find . -not -path './.git/*' -not -path './.git' | head -60
fi

echo ""
echo "============================================"
echo "📋 NEXT STEPS FOR PERSON 1:"
echo "============================================"
echo "1. cd incident-platform"
echo "2. Start coding services/alert-ingestion/main.py"
echo "3. Start coding services/incident-management/main.py"
echo "4. Test with: docker compose up database -d"
echo "5. Then: docker compose up alert-ingestion incident-management -d"
echo ""
echo "📋 TELL PERSON 2:"
echo "   - Fill in services/oncall-service/"
echo "   - Own run-pipeline.sh"
echo "   - Own monitoring/grafana-dashboards/*.json"
echo ""
echo "📋 TELL PERSON 3:"
echo "   - Fill in services/web-ui/"
echo "   - Optionally fill services/notification-service/"
echo "   - Own README.md"
echo "============================================"
