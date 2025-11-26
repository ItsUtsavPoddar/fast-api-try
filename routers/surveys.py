from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from datetime import datetime
import random
from bson import ObjectId

from models import (
    StoredSurvey,
    CreateSurveyRequest,
    UpdateSurveyRequest,
    SurveyResponse,
    SurveysListResponse,
    StorageStatsResponse,
    StoredVersion,
    SurveyConfig,
    UserSurveyResponse,
    SubmitSurveyResponseRequest,
    SubmitSurveyResponseResult,
    SurveyResponsesListResponse
)
from database import get_database

router = APIRouter(prefix="/api/surveys", tags=["surveys"])

def generate_survey_id() -> str:
    """Generate a random 4-digit survey ID"""
    return str(random.randint(1000, 9999))

def generate_version_id(survey_id: str, version: int) -> str:
    """Generate version ID (e.g., '1232v1')"""
    return f"{survey_id}v{version}"

async def get_collection():
    """Get surveys collection"""
    db = await get_database()
    return db["surveys"]

@router.post("/", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED)
async def create_survey(request: CreateSurveyRequest):
    """
    Create a new survey with all its versions
    Equivalent to: saveSurveyWithVersions()
    """
    try:
        collection = await get_collection()
        
        # Generate survey ID if not provided
        survey_id = request.surveyId
        if not survey_id:
            # Ensure unique ID
            while True:
                survey_id = generate_survey_id()
                existing = await collection.find_one({"surveyId": survey_id})
                if not existing:
                    break
        
        # Check if survey already exists
        existing_survey = await collection.find_one({"surveyId": survey_id})
        created_at = existing_survey["createdAt"] if existing_survey else datetime.utcnow()
        
        # Convert versions from frontend format to storage format
        stored_versions = []
        for v in request.versions:
            stored_version = StoredVersion(
                version=v["version"],
                versionId=generate_version_id(survey_id, v["version"]),
                config=SurveyConfig(**v["config"]),
                prompt=v.get("prompt"),
                timestamp=datetime.fromisoformat(v["timestamp"].replace("Z", "+00:00")) 
                    if isinstance(v["timestamp"], str) 
                    else v["timestamp"]
            )
            stored_versions.append(stored_version)
        
        # Create survey document
        survey = StoredSurvey(
            surveyId=survey_id,
            createdAt=created_at,
            versions=stored_versions
        )
        
        # Upsert survey
        await collection.replace_one(
            {"surveyId": survey_id},
            survey.model_dump(by_alias=True, exclude={"id"}),
            upsert=True
        )
        
        return SurveyResponse(
            success=True,
            survey=survey,
            message=f"Survey {survey_id} saved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save survey: {str(e)}"
        )

@router.put("/{survey_id}", response_model=SurveyResponse)
async def update_survey(survey_id: str, request: UpdateSurveyRequest):
    """
    Update an existing survey by adding/replacing versions
    Equivalent to: updateSurveyVersions()
    """
    try:
        collection = await get_collection()
        
        # Check if survey exists
        existing_survey = await collection.find_one({"surveyId": survey_id})
        if not existing_survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey {survey_id} not found"
            )
        
        # Convert versions
        stored_versions = []
        for v in request.versions:
            stored_version = StoredVersion(
                version=v["version"],
                versionId=generate_version_id(survey_id, v["version"]),
                config=SurveyConfig(**v["config"]),
                prompt=v.get("prompt"),
                timestamp=datetime.fromisoformat(v["timestamp"].replace("Z", "+00:00")) 
                    if isinstance(v["timestamp"], str) 
                    else v["timestamp"]
            )
            stored_versions.append(stored_version)
        
        # Update survey
        survey = StoredSurvey(
            surveyId=survey_id,
            createdAt=existing_survey["createdAt"],
            versions=stored_versions
        )
        
        await collection.replace_one(
            {"surveyId": survey_id},
            survey.model_dump(by_alias=True, exclude={"id"})
        )
        
        return SurveyResponse(
            success=True,
            survey=survey,
            message=f"Survey {survey_id} updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update survey: {str(e)}"
        )

@router.get("/{survey_id}", response_model=SurveyResponse)
async def get_survey(survey_id: str):
    """
    Get a specific survey by ID
    Equivalent to: getStoredSurvey()
    """
    try:
        collection = await get_collection()
        survey_doc = await collection.find_one({"surveyId": survey_id})
        
        if not survey_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey {survey_id} not found"
            )
        
        # Remove MongoDB _id field
        survey_doc.pop("_id", None)
        survey = StoredSurvey(**survey_doc)
        
        return SurveyResponse(
            success=True,
            survey=survey
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve survey: {str(e)}"
        )

@router.get("/{survey_id}/versions/{version}", response_model=dict)
async def get_survey_version(survey_id: str, version: int):
    """
    Get a specific version of a survey
    Equivalent to: getStoredVersion()
    """
    try:
        collection = await get_collection()
        survey_doc = await collection.find_one({"surveyId": survey_id})
        
        if not survey_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey {survey_id} not found"
            )
        
        # Find the specific version
        version_data = next(
            (v for v in survey_doc["versions"] if v["version"] == version),
            None
        )
        
        if not version_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found for survey {survey_id}"
            )
        
        return {
            "success": True,
            "version": version_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve version: {str(e)}"
        )

@router.delete("/{survey_id}", response_model=dict)
async def delete_survey(survey_id: str):
    """
    Delete a survey
    Equivalent to: deleteSurvey()
    """
    try:
        collection = await get_collection()
        result = await collection.delete_one({"surveyId": survey_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey {survey_id} not found"
            )
        
        return {
            "success": True,
            "message": f"Survey {survey_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete survey: {str(e)}"
        )

@router.get("/search/{query}", response_model=SurveysListResponse)
async def search_surveys(query: str):
    """
    Search surveys by ID (supports partial search)
    Equivalent to: searchSurveysByID()
    """
    try:
        collection = await get_collection()
        
        # Use regex for partial matching
        cursor = collection.find(
            {"surveyId": {"$regex": query, "$options": "i"}},
            {"_id": 0}
        ).sort("createdAt", -1)
        
        surveys_docs = await cursor.to_list(length=100)
        surveys = [StoredSurvey(**doc) for doc in surveys_docs]
        
        return SurveysListResponse(
            success=True,
            surveys=surveys,
            total=len(surveys)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search surveys: {str(e)}"
        )

@router.get("/", response_model=SurveysListResponse)
async def get_all_surveys(skip: int = 0, limit: int = 100):
    """
    Get all surveys (for listing)
    Equivalent to: getAllSurveys()
    """
    try:
        collection = await get_collection()
        
        cursor = collection.find(
            {},
            {"_id": 0}
        ).sort("createdAt", -1).skip(skip).limit(limit)
        
        surveys_docs = await cursor.to_list(length=limit)
        surveys = [StoredSurvey(**doc) for doc in surveys_docs]
        
        total = await collection.count_documents({})
        
        return SurveysListResponse(
            success=True,
            surveys=surveys,
            total=total
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve surveys: {str(e)}"
        )

@router.delete("/", response_model=dict)
async def clear_all_surveys():
    """
    Clear all surveys
    Equivalent to: clearAllSurveys()
    """
    try:
        collection = await get_collection()
        result = await collection.delete_many({})
        
        return {
            "success": True,
            "message": f"Deleted {result.deleted_count} surveys"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear surveys: {str(e)}"
        )

@router.get("/stats/storage", response_model=StorageStatsResponse)
async def get_storage_stats():
    """
    Get storage statistics
    Equivalent to: getStorageStats()
    """
    try:
        collection = await get_collection()
        
        surveys_docs = await collection.find({}, {"_id": 0}).to_list(length=None)
        surveys = [StoredSurvey(**doc) for doc in surveys_docs]
        
        total_versions = sum(len(survey.versions) for survey in surveys)
        
        # Calculate storage size
        import json
        storage_bytes = len(json.dumps(surveys_docs, default=str).encode('utf-8'))
        storage_mb = f"{storage_bytes / (1024 * 1024):.2f}"
        
        survey_info = [
            {
                "surveyId": survey.surveyId,
                "versionCount": len(survey.versions),
                "createdAt": survey.createdAt,
                "title": survey.versions[-1].config.title if survey.versions else "Untitled"
            }
            for survey in surveys
        ]
        
        return StorageStatsResponse(
            totalSurveys=len(surveys),
            totalVersions=total_versions,
            storageSizeBytes=storage_bytes,
            storageSizeMB=storage_mb,
            surveys=survey_info
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage stats: {str(e)}"
        )

@router.get("/{survey_id}/export")
async def export_survey(survey_id: str):
    """
    Export survey as JSON
    Equivalent to: exportSurveyAsJSON()
    """
    try:
        from fastapi.responses import StreamingResponse
        import json
        import io
        
        collection = await get_collection()
        survey_doc = await collection.find_one({"surveyId": survey_id})
        
        if not survey_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey {survey_id} not found"
            )
        
        survey_doc.pop("_id", None)
        json_str = json.dumps(survey_doc, indent=2, default=str)
        
        return StreamingResponse(
            io.BytesIO(json_str.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=survey_{survey_id}.json"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export survey: {str(e)}"
        )

@router.post("/responses/", response_model=SubmitSurveyResponseResult)
async def submit_survey_response(request: SubmitSurveyResponseRequest):
    """
    Submit a survey response
    Stores user answers to survey questions
    """
    try:
        from database import get_database
        from datetime import datetime
        
        db = await get_database()
        responses_collection = db["responses"]
        
        # Verify survey exists
        surveys_collection = db["surveys"]
        survey_doc = await surveys_collection.find_one({"surveyId": request.surveyId})
        
        if not survey_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey {request.surveyId} not found"
            )
        
        # Create response document
        import uuid
        response_id = str(uuid.uuid4())
        
        response_doc = {
            "responseId": response_id,
            "surveyId": request.surveyId,
            "versionId": request.versionId,
            "respondentInfo": request.respondentInfo,
            "answers": request.answers,
            "submittedAt": datetime.utcnow(),
            "completionTime": request.completionTime
        }
        
        await responses_collection.insert_one(response_doc)
        
        return SubmitSurveyResponseResult(
            success=True,
            responseId=response_id,
            message="Survey response submitted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit survey response: {str(e)}"
        )

@router.get("/responses/{survey_id}", response_model=SurveyResponsesListResponse)
async def get_survey_responses(survey_id: str):
    """
    Get all responses for a specific survey
    Returns list of user submissions
    """
    try:
        from database import get_database
        
        db = await get_database()
        responses_collection = db["responses"]
        
        # Get all responses for this survey
        response_docs = await responses_collection.find(
            {"surveyId": survey_id},
            {"_id": 0}
        ).to_list(length=None)
        
        responses = [UserSurveyResponse(**doc) for doc in response_docs]
        
        return SurveyResponsesListResponse(
            success=True,
            responses=responses,
            count=len(responses)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get survey responses: {str(e)}"
        )

@router.post("/analyze-historical")
async def analyze_historical_surveys(survey_ids: str):
    """
    Fetch multiple surveys with their responses for AI analysis
    survey_ids: comma-separated survey IDs (e.g., "1234,5678,9012")
    Returns survey configs and all responses for AI to analyze
    """
    try:
        from database import get_database
        
        # Parse and validate survey IDs
        id_list = [sid.strip() for sid in survey_ids.split(",") if sid.strip()]
        
        if len(id_list) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No survey IDs provided"
            )
        
        if len(id_list) > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 5 surveys allowed for analysis"
            )
        
        db = await get_database()
        surveys_collection = db["surveys"]
        responses_collection = db["responses"]
        
        result = []
        
        for survey_id in id_list:
            # Fetch survey
            survey_doc = await surveys_collection.find_one(
                {"surveyId": survey_id},
                {"_id": 0}
            )
            
            if not survey_doc:
                # Skip missing surveys instead of failing
                continue
            
            # Fetch all responses for this survey
            response_docs = await responses_collection.find(
                {"surveyId": survey_id},
                {"_id": 0}
            ).to_list(length=None)
            
            result.append({
                "survey": StoredSurvey(**survey_doc),
                "responses": [UserSurveyResponse(**doc) for doc in response_docs]
            })
        
        if len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="None of the provided survey IDs were found"
            )
        
        return {
            "success": True,
            "data": result,
            "count": len(result)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch historical surveys: {str(e)}"
        )
