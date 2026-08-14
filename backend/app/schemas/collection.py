from datetime import datetime
from pydantic import BaseModel, ConfigDict

class CollectionCreate(BaseModel):
    name:str
    description: str|None = None

class CollectionUpdate(BaseModel):
    name:str|None = None
    description:str|None = None

class CollectionResponse(BaseModel):
    id:int
    name:str
    description: str|None
    owner_id:int
    created_at:datetime
    updated_at:datetime

    model_config = ConfigDict(from_attributes= True)