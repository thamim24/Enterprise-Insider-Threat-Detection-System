# 🛡️ Enterprise Insider Threat Detection Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![React](https://img.shields.io/badge/React-18.2-61DAFB.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![ML](https://img.shields.io/badge/ML-Powered-red.svg)

**An ML-powered, explainable insider threat detection system for enterprise document security**

[Features](#-features) • [Architecture](#-architecture) • [ML Algorithms](#-ml--nlp-algorithms) • [Installation](#-installation) • [Usage](#-usage) • [API](#-api-endpoints)

</div>

---

## 📋 Overview

The **Enterprise Insider Threat Detection Platform** is a comprehensive security solution that uses **Machine Learning** and **Natural Language Processing** to detect, analyze, and explain potential insider threats in real-time. The platform monitors document access patterns, classifies document sensitivity, verifies data integrity, and provides explainable AI insights for security analysts.

### Key Capabilities

- 🔍 **Real-time Behavioral Anomaly Detection** - Identifies unusual user behavior patterns
- 📄 **Automatic Document Sensitivity Classification** - ML-based sensitivity level prediction
- 🔐 **Document Integrity Verification** - Hash-based and semantic tampering detection
- ⚠️ **Intelligent Alert Generation** - Context-aware risk scoring and alerting
- 🧠 **Explainable AI (XAI)** - SHAP and LIME explanations for model decisions
- 📊 **Interactive Security Dashboard** - Real-time monitoring and analytics
- ⚡ **Event-Driven Architecture** - Asynchronous queue-based processing with WebSocket live updates
- 🔴 **Live Alert Streaming** - Instant notifications for high-risk events via WebSocket
- ⚡ **Event-Driven Architecture** - Asynchronous queue-based processing with WebSocket live updates
- 🔴 **Live Alert Streaming** - Instant notifications for high-risk events via WebSocket

---

## 🏗️ Architecture

### Real-Time Event-Driven Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + Vite + WebSocket)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │    User      │  │   Analyst    │  │   Alerts     │  │   Reports    │    │
│  │  Dashboard   │  │  Dashboard   │  │    Panel     │  │    View      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└────────────┬───────────────────────────────────┬──────────────────────────────┘
             │ REST API                       │ WebSocket (Live Updates)
┌────────────▼───────────────────────────────────▼──────────────────────────────┐
│                    BACKEND (FastAPI + SQLAlchemy + asyncio)                  │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                         API Layer (FastAPI)                           │    │
│  │  /auth  │  /documents  │  /events  │  /alerts  │  /ml  │  /reports   │    │
│  └───────────────────────────────┬──────────────────────────────────────┘    │
│                                  │                                            │
│                                  ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                  EVENT QUEUE (asyncio.Queue - 1000 cap)               │    │
│  │               Fast API Response ◄─── Enqueue Event ◄─── User Action  │    │
│  └──────────────────────────────┬───────────────────────────────────────┘    │
│                                 │                                             │
│                                 ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │            BACKGROUND ML WORKER (async forever-running)               │    │
│  │                                                                       │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐     │    │
│  │  │ Behavioral │  │ Sensitivity│  │ Integrity  │  │    Risk    │     │    │
│  │  │  Anomaly   │  │ Classifier │  │  Verifier  │  │   Fusion   │     │    │
│  │  │ (IsoForest)│  │(NLP/Keywrd)│  │(Hash+Embed)│  │  Engine    │     │    │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘     │    │
│  │                         │                                            │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │         EXPLAINABILITY LAYER (SHAP + LIME)                  │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                         │                                            │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │         INTELLIGENT ALERT DECISION ENGINE                   │    │    │
│  │  │  • CRITICAL (≥80%): Always alert                            │    │    │
│  │  │  • HIGH (≥60%): Multi-factor evaluation                     │    │    │
│  │  │  • Document tampering detection                             │    │    │
│  │  │  • Cross-department sensitive access                        │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  └──────────────────────────────┬───────────────────────────────────────┘    │
│                                 │                                             │
│                                 ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                DATABASE (SQLite + SQLAlchemy)                         │    │
│  │  Users │ Documents │ Events │ Alerts │ Explanations │ Sessions       │    │
│  └──────────────────────────────┬───────────────────────────────────────┘    │
│                                 │                                             │
│                                 ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │            WEBSOCKET MANAGER (Multi-client Broadcasting)              │    │
│  │  • new_alert events → All connected analysts                          │    │
│  │  • new_event streams → Real-time activity feed                        │    │
│  │  • Complete alert objects with XAI metadata                           │    │
│  └──────────────────────────────┬───────────────────────────────────────┘    │
└─────────────────────────────────┴───────────────────────────────────────────┘
                                  ▲
                                  │ Live Push Notifications
                   Frontend Dashboard (Auto-updates)
```

### Architecture Highlights

**🚀 Asynchronous Processing Pipeline**
- User actions return immediately (< 50ms response)
- ML processing happens in background worker
- No blocking operations in API layer

**⚡ Event Queue System**
- `asyncio.Queue` with 1000 event capacity
- Decouples API response from ML processing
- Ensures system responsiveness under load

**🔴 Real-Time WebSocket Broadcasting**
- Multi-client connection manager
- Instant alert notifications to all connected analysts
- Complete alert objects with risk scores and XAI explanations
- Auto-reconnection on connection loss

**🧠 Intelligent Alert Generation**
- Comprehensive alert decision logic beyond simple thresholds
- Multi-factor evaluation for HIGH risk events
- Context-aware rules (tampering, cross-dept access, after-hours)
- Prevents alert fatigue with smart filtering

---

## 🤖 ML & NLP Algorithms

### 1. Behavioral Anomaly Detection

| Component | Technology | Description |
|-----------|------------|-------------|
| **Algorithm** | Isolation Forest | Unsupervised anomaly detection for user behavior |
| **Features** | 16 behavioral features | Event count, bytes transferred, temporal patterns, cross-department access |
| **Scaling** | StandardScaler | Feature normalization for consistent model performance |

**Behavioral Features Extracted:**
- `total_events_24h` - Activity volume in 24 hours
- `total_bytes_24h` - Data transfer volume
- `unique_documents_24h` - Document access diversity
- `is_after_hours` - Temporal anomaly flag (outside 9 AM - 5 PM)
- `is_weekend` - Weekend activity flag
- `cross_dept_access_count` - Cross-department access frequency
- `cross_dept_ratio` - Ratio of cross-department to total access
- `download_count`, `modify_count`, `view_count` - Action patterns
- `confidential_access_count` - Sensitive document access
- `unique_ips`, `unique_devices` - Session anomalies

### 2. Document Sensitivity Classification

| Component | Technology | Description |
|-----------|------------|-------------|
| **Primary Method** | Keyword-based NLP | Pattern matching for sensitivity indicators |
| **Advanced Method** | Zero-Shot Classification | HuggingFace Transformers (BART-large-MNLI) |
| **Hybrid Detection** | ML vs Declared Mismatch | Detects when user-declared sensitivity doesn't match ML prediction |

**Keyword Categories:**
- **Confidential**: Financial (salary, revenue, merger), Personal (SSN, medical), Security (passwords, API keys), Legal (contracts, NDA)
- **Internal**: Operations (policies, procedures), Projects (requirements, specs), Communications (memos, updates)
- **Public**: Marketing (press releases, brochures), General (announcements, public info)

**Regex Patterns for PII Detection:**
- SSN: `\b\d{3}-\d{2}-\d{4}\b`
- Credit Cards: `\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b`
- API Keys: `\b[A-Za-z0-9]{32,}\b`
- Money amounts, percentages, passwords

### 3. Document Integrity Verification

| Component | Technology | Description |
|-----------|------------|-------------|
| **Hash Verification** | SHA-256 | Cryptographic hash comparison for exact change detection |
| **Semantic Similarity** | Sentence Transformers | all-MiniLM-L6-v2 model for semantic comparison |
| **Tampering Severity** | Threshold-based | Minor (>95%), Moderate (85-95%), Major (<85%) similarity |

### 4. Risk Fusion Engine

| Component | Weight | Description |
|-----------|--------|-------------|
| **Behavior Score** | 40% | Anomaly detection contribution |
| **Sensitivity Score** | 30% | Document classification risk |
| **Integrity Score** | 30% | Tampering detection risk |

**Risk Level Thresholds:**
- **CRITICAL**: Risk Score ≥ 0.8
- **HIGH**: Risk Score ≥ 0.6
- **MEDIUM**: Risk Score ≥ 0.4
- **LOW**: Risk Score < 0.4

**Multipliers:**
- Cross-department access: 1.5x
- After-hours activity: 1.3x
- Download/Modify actions: 1.2x
- Confidential documents: 1.4x

### 5. Explainable AI (XAI)

| Component | Technology | Use Case |
|-----------|------------|----------|
| **SHAP** | TreeExplainer / KernelExplainer | Behavioral anomaly explanation |
| **LIME** | LimeTextExplainer | Document classification explanation |

**SHAP (SHapley Additive exPlanations):**
- Feature importance ranking for each prediction
- Direction of influence (positive/negative impact)
- Natural language explanations generated

**LIME (Local Interpretable Model-agnostic Explanations):**
- Word-level importance for text classification
- HTML visualization of highlighted terms
- Class probability explanations

---

## 🛠️ Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.9+ | Core programming language |
| FastAPI | 0.109.2 | Modern async web framework |
| SQLAlchemy | 2.0.25 | ORM for database operations |
| SQLite | - | Lightweight database |
| Uvicorn | 0.27.1 | ASGI server |
| Pydantic | 2.6.1 | Data validation |
| JWT (python-jose) | 3.3.0 | Authentication tokens |
| Passlib + Bcrypt | - | Password hashing |
| asyncio | - | Event queue and background workers |
| WebSocket | - | Real-time bidirectional communication |

### Machine Learning & NLP
| Technology | Version | Purpose |
|------------|---------|---------|
| scikit-learn | 1.4.0 | Isolation Forest, StandardScaler |
| NumPy | 1.26.4 | Numerical computations |
| Pandas | 2.2.0 | Data manipulation |
| Sentence Transformers | 2.3.1 | Semantic similarity embeddings |
| Transformers | 4.37.2 | Zero-shot NLP classification |
| PyTorch | 2.2.0 | Deep learning backend |
| SHAP | 0.44.1 | Model explainability |
| LIME | 0.2.0.1 | Text classification explainability |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2 | UI library |
| Vite | 5.0 | Build tool & dev server |
| TailwindCSS | 3.3.5 | Utility-first CSS |
| React Query | 5.8.4 | Data fetching & caching |
| React Router | 6.20 | Client-side routing |
| Recharts | 2.10.3 | Data visualization |
| Lucide React | 0.294 | Icon library |
| Axios | 1.6.2 | HTTP client |
| diff | 8.0.2 | Text diff visualization |
| WebSocket API | Native | Real-time event streaming |

---

## 📁 Project Structure

```
enterprise_insider_threat/
├── backend/
│   ├── api/                      # REST API endpoints
│   │   ├── alerts.py             # Alert management
│   │   ├── auth.py               # Authentication & authorization
│   │   ├── documents.py          # Document operations
│   │   ├── events.py             # User event tracking
│   │   ├── ml_status.py          # ML pipeline status
│   │   └── reports.py            # Security reports
│   ├── core/                     # Core configuration
│   │   ├── config.py             # App settings
│   │   └── security.py           # JWT & password handling
│   ├── db/                       # Database layer
│   │   ├── database.py           # SQLAlchemy setup
│   │   └── models.py             # ORM models
│   ├── ml/                       # ML utilities
│   │   └── sensitivity_classifier.py  # Hybrid sensitivity detection
│   ├── ml_engine/                # ML Pipeline
│   │   ├── pipeline.py           # Main orchestrator
│   │   ├── behavior/             # Behavioral analysis
│   │   │   └── anomaly.py        # Isolation Forest detector
│   │   ├── documents/            # Document analysis
│   │   │   ├── integrity.py      # Hash & semantic verification
│   │   │   └── sensitivity.py    # NLP classification
│   │   ├── explainability/       # XAI engines
│   │   │   ├── shap_engine.py    # SHAP explanations
│   │   │   └── lime_engine.py    # LIME explanations
│   │   └── fusion/               # Risk calculation
│   │       └── risk_engine.py    # Multi-signal fusion
│   ├── storage/                  # File storage
│   ├── streaming/                # Real-time components
│   │   └── ml_worker.py          # Background ML processor
│   └── app.py                    # FastAPI application
├── frontend/
│   ├── src/
│   │   ├── api/                  # API client
│   │   │   └── client.js         # Axios configuration
│   │   ├── components/           # Reusable UI components
│   │   │   ├── DiffViewer.jsx    # Document diff display
│   │   │   ├── LimeViewer.jsx    # LIME explanation viewer
│   │   │   ├── RiskBadge.jsx     # Risk level indicator
│   │   │   └── ShapChart.jsx     # SHAP feature importance
│   │   ├── pages/                # Main views
│   │   │   ├── AnalystDashboard.jsx  # Security analyst view
│   │   │   ├── UserDashboard.jsx     # User document access
│   │   │   ├── Alerts.jsx            # Alert management
│   │   │   ├── Reports.jsx           # Security reports
│   │   │   └── Login.jsx             # Authentication
│   │   ├── utils/                # Utility functions
│   │   │   └── dateUtils.js      # IST date formatting
│   │   ├── App.jsx               # Main app component
│   │   └── main.jsx              # Entry point
│   ├── package.json              # Frontend dependencies
│   └── vite.config.js            # Vite configuration
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## 🚀 Installation

### Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **npm or yarn**

### Backend Setup

```bash
# Navigate to project directory
cd enterprise_insider_threat

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend server
uvicorn backend.app:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

---

## 📖 Usage

### Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Regular User | `jsmith` | `password123` |
| Security Analyst | `analyst` | `analyst123` |

### User Dashboard Features

1. **Document Browser** - View, upload, download, modify documents
2. **Activity Timeline** - Track your document access history
3. **Risk Indicators** - See real-time risk scores for your actions

### Analyst Dashboard Features

1. **Anomaly Timeline** - 24-hour risk score visualization
2. **Alert Distribution** - Pie chart of alert severities
3. **Top Risk Users** - Ranked list with risk scores
4. **SHAP Feature Importance** - ML model insights
5. **Document Integrity Alerts** - Tampering detection with diff view
6. **Real-time Activity Feed** - Live WebSocket stream of all user actions
7. **Live Alert Notifications** - Instant push alerts for high-risk events (CRITICAL, HIGH, MEDIUM, LOW)
8. **Auto-updating Dashboard** - No manual refresh needed, data updates automatically
9. **Comprehensive Alert List** - Time-sorted display showing all severity levels (100 most recent)

---

## 🔌 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/register` | User registration |
| GET | `/api/auth/me` | Current user info |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/documents/` | List all documents |
| POST | `/api/documents/upload` | Upload document |
| GET | `/api/documents/{id}` | Get document details |
| PUT | `/api/documents/{id}` | Modify document |
| DELETE | `/api/documents/{id}` | Delete document |

### Events
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/events/` | List events |
| GET | `/api/events/user/{user_id}` | User's events |
| GET | `/api/events/all` | All events (analyst) |

### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts/` | List alerts |
| PUT | `/api/alerts/{id}` | Update alert status |
| GET | `/api/alerts/stats` | Alert statistics |

### ML Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ml/status` | Pipeline status |
| GET | `/api/ml/anomaly-timeline` | Anomaly scores over time |
| GET | `/api/ml/top-risk-users` | Highest risk users |
| GET | `/api/ml/feature-importance` | SHAP feature importance |
| GET | `/api/ml/document-modifications` | Recent modifications |

---

## 📊 Real-Time ML Pipeline Flow

```
User Action (view/download/upload/modify)
         │
         ▼
    ┌─────────────────────────────────────────┐
    │    REST API Endpoint (FastAPI)          │
    │    • Immediate HTTP 200 Response        │
    │    • Event → asyncio.Queue (enqueue)    │
    └────────┬────────────────────────────────┘
             │ (User sees instant response)
             │
             ▼
    ┌─────────────────────────────────────────┐
    │   Background ML Worker (async loop)     │
    │   Dequeues events continuously          │
    └────────┬────────────────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │   Behavioral    │──► Isolation Forest ──► Anomaly Score
    │    Analysis     │    (16 features)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   Sensitivity   │──► Keyword/NLP ──► Classification + Mismatch Detection
    │  Classification │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   Integrity     │──► SHA-256 + Embeddings ──► Tamper Severity
    │  Verification   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  Risk Fusion    │──► Weighted Combination ──► Final Risk Score
    │    Engine       │    + Multipliers
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Explainability  │──► SHAP (Behavior) + LIME (Text) ──► Human-readable
    │    Layer        │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────────────────────────────┐
    │  Intelligent Alert Decision Logic       │
    │  • CRITICAL (≥80%): Always create alert │
    │  • HIGH (≥60%): Multi-factor check      │
    │  • Tampering detected: Always alert     │
    │  • Cross-dept sensitive: Always alert   │
    │  • After-hours + confidential: Alert    │
    └────────┬────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────┐
    │  Database Storage (Events + Alerts)     │
    │  • Event entity with risk_score         │
    │  • Alert entity (if conditions met)     │
    │  • Explanation entity (SHAP/LIME)       │
    └────────┬────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────┐
    │  WebSocket Broadcasting                 │
    │  • new_event → Activity feed            │
    │  • new_alert → Alert panel (instant)    │
    │  • Complete objects with XAI metadata   │
    └────────┬────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────┐
    │  Frontend Dashboard (Auto-updates)      │
    │  • Live alerts appear instantly         │
    │  • Activity feed streams in real-time   │
    │  • No manual refresh required           │
    └─────────────────────────────────────────┘

⏱️ Timeline:
• API Response: < 50ms (immediate)
• ML Processing: 1-3 seconds (background)
• WebSocket Push: < 100ms after alert creation
• Total user-to-analyst latency: ~3 seconds for high-risk alerts
```

---

## 🔐 Security Features

- **JWT Authentication** - Secure token-based auth with expiration
- **Password Hashing** - Bcrypt with salt for credential storage
- **Role-Based Access** - User vs Analyst permissions
- **Audit Logging** - All document actions tracked
- **Cross-Department Detection** - Flags unauthorized access patterns
- **After-Hours Monitoring** - Temporal anomaly detection

---

## ✨ Recent Upgrades

### Real-Time Architecture (v2.0)

✅ **Completed Features:**
- **Event-Driven Backend**: Asynchronous queue-based processing pipeline
- **Background ML Worker**: Non-blocking ML inference with `asyncio.Queue`
- **WebSocket Integration**: Live bidirectional communication for instant updates
- **Intelligent Alert Logic**: Comprehensive multi-factor alert decision engine
- **Alert Priority System**: CRITICAL, HIGH, MEDIUM, LOW with context-aware rules
- **Live Dashboard Updates**: Auto-refreshing analyst view with WebSocket push
- **Complete Alert Objects**: Full metadata including risk scores and XAI explanations
- **Enhanced Sorting**: Time-first alert display showing all severity levels
- **Increased Pagination**: 100 alerts per page (previously 20)
- **Top Risk Events**: 25 events displayed in reports (previously 10)
- **Error Handling**: Robust LIME explanation processing with graceful degradation

### Performance Improvements
- API response time: **< 50ms** (ML processing decoupled)
- Real-time latency: **~3 seconds** from user action to analyst notification
- Queue capacity: **1000 events** (handles burst traffic)
- WebSocket broadcast: **< 100ms** per message

## 📈 Future Enhancements

- [ ] LDAP/Active Directory integration
- [ ] Email/Slack alert notifications
- [ ] Advanced NLP with fine-tuned transformers
- [ ] Graph-based user behavior modeling
- [ ] Integration with SIEM systems
- [ ] Batch processing for historical analysis
- [ ] Export reports to PDF/Excel
- [ ] Redis/RabbitMQ for distributed queue (scale beyond single server)
- [ ] Kafka for event streaming at enterprise scale

---

## 📄 License

This project is licensed under the MIT License.

---

## 👥 Contributors

Built with ❤️ for enterprise security

---

<div align="center">

**[⬆ Back to Top](#-enterprise-insider-threat-detection-platform)**

</div>
