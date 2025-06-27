from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class CompanyAnalysis(BaseModel):
    # defining schema
    pricing_model: str
    is_open_source: Optional[bool] = None
    tech_stack: List[str] = []
    description: str = ""
    api_available: Optional[bool] = None
    language_support: List[str] = []
    integration_capablities = List[str] = []


class CompanyInfo(BaseModel):
    name: str
    description: str
    website: str
    pricing_model: Optional[str] = None
    is_open_source: Optional[bool] = None
    tech_stack: List[str] = []
    competetitors: List[str] = None
    
    api_available: Optional[bool] = None
    language_support: list[str] = []
    integration_capablities: List[str] = []
    developer_experience_rating = Optional[str] = None
    
    
class ResearchState(BaseModel):
    query: str
    extracted_tools: List[str] = []
    companies: List[CompanyInfo] = []
    search_results: List[Dict[str, Any]] = []
    analysis: Optional[str] = None
    
    