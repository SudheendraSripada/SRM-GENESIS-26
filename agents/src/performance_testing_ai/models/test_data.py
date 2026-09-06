from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class DataStrategy(str, Enum):
    SYNTHETIC_GENERATED = "synthetic_generated"
    PRE_SEEDED = "pre_seeded"
    CSV_FEEDER = "csv_feeder"
    DYNAMIC_PARAM = "dynamic_parameterization"

class SelectionMode(str, Enum):
    RANDOM = "random"
    SEQUENTIAL = "sequential"
    UNIQUE = "unique"

class DatasetRequirement(BaseModel):
    name: str = Field(..., description="Dataset name e.g. user_credentials, cart_items")
    description: str = Field(..., description="Purpose and contents of the dataset")
    volume_needed: int = Field(..., ge=1, description="Minimum number of records required")
    fields: List[str] = Field(default_factory=list, description="Data schema fields e.g. ['username', 'password']")
    strategy: DataStrategy = Field(default=DataStrategy.SYNTHETIC_GENERATED, description="Provisioning strategy")
    is_sensitive: bool = Field(default=False, description="Whether dataset contains sensitive or PII data")

class UserProfileSpec(BaseModel):
    role: str = Field(..., description="User role e.g. 'shopper', 'admin'")
    count: int = Field(..., ge=1, description="Number of virtual accounts allocated")
    auth_required: bool = Field(default=True, description="Whether this profile requires authenticated session")
    credentials_source: str = Field(default="synthetic_pool", description="Origin of authentication credentials")

class ParameterizationRule(BaseModel):
    parameter_name: str = Field(..., description="Parameter key name e.g. 'product_id'")
    source_dataset: str = Field(..., description="Dataset supplying values")
    selection_mode: SelectionMode = Field(default=SelectionMode.RANDOM, description="Access pattern across VUs")

class TestDataPlan(BaseModel):
    """
    Contract produced by the Test Data Agent.
    Specifies deterministic data provisioning rules, volumes, authentication needs, and correlation.
    Never attempts to output millions of raw rows directly from an LLM.
    """
    __test__ = False
    data_plan_id: str = Field(..., description="Unique identifier for the test data plan")
    plan_id: str = Field(..., description="Associated performance plan ID")
    users_required: int = Field(..., ge=1, description="Total virtual users requiring test data")
    unique_users_required: bool = Field(default=True, description="Whether each VU must use an isolated account")
    payload_requirements: List[str] = Field(default_factory=list, description="Schemas or payload fields required")
    product_data_requirements: List[str] = Field(default_factory=list, description="Catalog, SKU, or inventory data needs")
    authentication_requirements: List[str] = Field(default_factory=list, description="Token, cookie, or credential requirements")
    correlation_requirements: List[str] = Field(default_factory=list, description="Dynamic values correlated between calls (e.g. cart_id, token)")
    data_generation_strategy: str = Field(..., description="Strategy for generating or loading data deterministically")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions regarding test data accessibility")

    # Detailed specifications
    datasets_needed: List[DatasetRequirement] = Field(default_factory=list, description="Detailed datasets catalog")
    user_profiles: List[UserProfileSpec] = Field(default_factory=list, description="Virtual user authentication profiles")
    parameterization_rules: List[ParameterizationRule] = Field(default_factory=list, description="Parameter binding rules")
