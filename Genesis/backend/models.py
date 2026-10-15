from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    dataset_id: str


class Split(StrEnum):
    DISCOVERY = "CALIBRATION_DISCOVERY"
    SELECTION = "CALIBRATION_SELECTION"
    HOLDOUT = "HOLDOUT"
    DEMO = "DEMO"


class Customer(Record):
    display_name: str
    customer_type: Literal["INDIVIDUAL", "ORGANIZATION"]
    onboarded_at: AwareDatetime
    pep: bool | None = False
    synthetic_sanctions_flag: bool | None = False
    deceased_at: AwareDatetime | None = None
    profile_context: str = Field(default="", max_length=2000)


class Account(Record):
    customer_id: str
    opened_at: AwareDatetime
    prior_activity_at: AwareDatetime | None
    history_complete_from: AwareDatetime | None
    currency: str = "AUD"
    status: Literal["OPEN", "CLOSED"] = "OPEN"


class Transaction(Record):
    account_id: str
    customer_id: str
    occurred_at: AwareDatetime
    original_minor: Annotated[StrictInt, Field(ge=0)]
    currency: Literal["AUD", "USD", "GBP", "EUR"]
    amount_aud_minor: Annotated[StrictInt, Field(ge=0)]
    fx_rate_id: str
    direction: Literal["CREDIT", "DEBIT"]
    type: Literal["CASH", "WIRE", "CRYPTO", "TRANSFER", "PAYMENT"]
    counterparty_id: str | None
    counterparty_sanctions_flag: bool | None = False
    description: str = Field(default="", max_length=2000)


class Case(Record):
    scenario_family: str
    split: Split
    customer_id: str
    account_ids: list[str]
    trigger_transaction_id: str
    history_transaction_ids: list[str]
    data_quality: list[str] = Field(default_factory=list)


class Dataset(BaseModel):
    id: str
    seed: int
    version: str
    customers: dict[str, Customer]
    accounts: dict[str, Account]
    transactions: dict[str, Transaction]
    cases: dict[str, Case]
    reference_labels: dict[str, Literal["SUSPICIOUS", "BENIGN", "INCONCLUSIVE"]]
    reference_reasons: dict[str, str]
    manifest_hash: str


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: Literal["TRUE_POSITIVE", "FALSE_POSITIVE", "INCONCLUSIVE"]
    notes: str = Field(min_length=1, max_length=2000)
    override_action: Literal["ESCALATE", "REVIEW", "MONITOR", "CLOSE"] | None = None
    expected_revision: int = Field(ge=0)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(min_length=1, max_length=30)


class RiskExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findings: list[Finding] = Field(max_length=8)
    counter_evidence: list[Finding] = Field(max_length=5)
    limitations: list[str] = Field(max_length=8)


class Categorization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    primary_typology: Literal["STRUCTURING", "LAYERING", "SANCTIONS_EXPOSURE", "POTENTIAL_IDENTITY_MISUSE", "PEP_REVIEW", "LOW_RISK", "OTHER", "UNDETERMINED"]
    suggested_action: Literal["ESCALATE", "REVIEW", "MONITOR", "CLOSE"]
    rationale: Finding
    uncertainty: Literal["LOW", "MEDIUM", "HIGH"]


class Investigation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    overview: Finding
    key_findings: list[Finding] = Field(max_length=8)
    counter_evidence: list[Finding] = Field(max_length=5)
    missing_information: list[str] = Field(max_length=8)
    next_steps: list[str] = Field(max_length=8)
    limitations: list[str] = Field(max_length=8)
