# Survey Generator Backend API

FastAPI backend with MongoDB that replaces the localStorage implementation in the frontend.

## Setup

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Environment**
Create a `.env` file:
```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=survey_generator
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

3. **Run MongoDB**
```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or install MongoDB locally
```

4. **Start the Server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

All endpoints match the localStorage functions from the frontend:

### Survey Operations

- `POST /api/surveys/` - Create/save survey (saveSurveyWithVersions)
- `PUT /api/surveys/{survey_id}` - Update survey versions (updateSurveyVersions)
- `GET /api/surveys/{survey_id}` - Get survey by ID (getStoredSurvey)
- `GET /api/surveys/{survey_id}/versions/{version}` - Get specific version (getStoredVersion)
- `DELETE /api/surveys/{survey_id}` - Delete survey (deleteSurvey)

### Search & List

- `GET /api/surveys/search/{query}` - Search surveys (searchSurveysByID)
- `GET /api/surveys/` - Get all surveys (getAllSurveys)
  - Query params: `skip` (default: 0), `limit` (default: 100)

### Utility

- `DELETE /api/surveys/` - Clear all surveys (clearAllSurveys)
- `GET /api/surveys/stats/storage` - Get storage stats (getStorageStats)
- `GET /api/surveys/{survey_id}/export` - Export survey as JSON (exportSurveyAsJSON)

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Data Structure

The API uses the same data structures as the frontend:

```typescript
interface StoredSurvey {
  surveyId: string        // 4-digit ID
  createdAt: Date
  versions: StoredVersion[]
}

interface StoredVersion {
  version: number
  versionId: string       // e.g., "1232v1"
  config: SurveyConfig
  prompt?: string
  timestamp: Date
}
```

## MongoDB Schema

Collections:
- `surveys` - Stores all survey documents with embedded versions

Indexes:
- `surveyId` (unique)
- `createdAt` (descending)
- `versions.version`

## Deployment

### Production Setup

1. Update `.env` with production MongoDB URL
2. Set `CORS_ORIGINS` to your frontend URL
3. Run with production server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t survey-api .
docker run -p 8000:8000 --env-file .env survey-api
```

## Integration with Frontend

Replace the localStorage imports in your frontend:

```typescript
// Before
import { saveSurveyWithVersions } from '@/lib/survey-storage'

// After
const API_URL = 'http://localhost:8000/api/surveys'

async function saveSurveyWithVersions(versions, surveyId?) {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ versions, surveyId })
  })
  return response.json()
}
```
