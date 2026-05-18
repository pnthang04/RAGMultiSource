from pydantic import BaseModel, ConfigDict


class MongoBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
