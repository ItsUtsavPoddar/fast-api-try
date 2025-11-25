from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Survey Type Models (matching frontend survey-types.ts)

class QuestionType(str, Enum):
    text = "text"
    textarea = "textarea"
    number = "number"
    select = "select"
    radio = "radio"
    checkbox = "checkbox"
    rating = "rating"
    date = "date"

class ConditionOperator(str, Enum):
    equals = "equals"
    notEquals = "notEquals"
    in_op = "in"
    notIn = "notIn"
    gt = "gt"
    lt = "lt"
    contains = "contains"
    notContains = "notContains"
    isTruthy = "isTruthy"
    isFalsy = "isFalsy"

class Condition(BaseModel):
    questionId: str
    operator: ConditionOperator
    value: Optional[Any] = None

class VisibilityRule(BaseModel):
    all: Optional[List[Condition]] = None
    any: Optional[List[Condition]] = None
    none: Optional[List[Condition]] = None

class ValidationRules(BaseModel):
    required: Optional[bool] = None
    min: Optional[float] = None
    max: Optional[float] = None
    minLength: Optional[int] = None
    maxLength: Optional[int] = None
    pattern: Optional[str] = None
    minSelected: Optional[int] = None
    maxSelected: Optional[int] = None
    maxStars: Optional[int] = None

class OptionItem(BaseModel):
    value: str
    label: str

class Question(BaseModel):
    id: str
    type: QuestionType
    label: str
    description: Optional[str] = None
    placeholder: Optional[str] = None
    defaultValue: Optional[Any] = None
    visibleIf: Optional[VisibilityRule] = None
    validation: Optional[ValidationRules] = None
    options: Optional[List[OptionItem]] = None  # For select, radio, checkbox

class Section(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    visibleIf: Optional[VisibilityRule] = None
    questions: List[Question]

class SurveyConfig(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    sections: List[Section]

# Storage Models (matching frontend survey-storage.ts)

class StoredVersion(BaseModel):
    version: int
    versionId: str
    config: SurveyConfig
    prompt: Optional[str] = None
    timestamp: datetime

class StoredSurvey(BaseModel):
    surveyId: str
    createdAt: datetime
    versions: List[StoredVersion]

class StoredSurveyInDB(StoredSurvey):
    id: Optional[str] = Field(None, alias="_id")

# Request/Response Models

class CreateSurveyRequest(BaseModel):
    versions: List[Dict[str, Any]]  # ConfigVersion from frontend
    surveyId: Optional[str] = None

class UpdateSurveyRequest(BaseModel):
    versions: List[Dict[str, Any]]  # ConfigVersion from frontend

class SurveyResponse(BaseModel):
    success: bool
    survey: Optional[StoredSurvey] = None
    message: Optional[str] = None

class SurveysListResponse(BaseModel):
    success: bool
    surveys: List[StoredSurvey]
    total: int

class StorageStatsResponse(BaseModel):
    totalSurveys: int
    totalVersions: int
    storageSizeBytes: int
    storageSizeMB: str
    surveys: List[Dict[str, Any]]
