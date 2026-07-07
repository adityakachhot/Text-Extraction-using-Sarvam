from typing import Optional
from pydantic import BaseModel, Field

class BillExtractionResult(BaseModel):
    """Pydantic model representing the flat normalized structure of an electricity bill."""
    document_type_match: bool = Field(
        ...,
        description="True if the document is an electricity bill, False otherwise."
    )
    discom: Optional[str] = Field(
        None,
        description="Name of the electricity Distribution Company (DISCOM)."
    )
    consumer_number: Optional[str] = Field(
        None,
        description="Unique identifier of the electricity consumer/connection."
    )
    total_bill_amount: Optional[float] = Field(
        None,
        description="Total billing amount payable on or before the due date, including previous arrears."
    )
    bill_amount: Optional[float] = Field(
        None,
        description="Electricity charge for the current billing cycle only."
    )
    arrears: Optional[float] = Field(
        None,
        description="Previous outstanding dues or unpaid balance."
    )
    overdue_months_count: Optional[int] = Field(
        None,
        description="Number of months the bill has been overdue."
    )
    name: Optional[str] = Field(
        None,
        description="Name of the consumer exactly as printed on the bill."
    )
    fathers_name: Optional[str] = Field(
        None,
        description="Consumer's father's name (if available)."
    )
    address: Optional[str] = Field(
        None,
        description="Consumer service or billing address exactly as printed."
    )
    sanction_load: Optional[float] = Field(
        None,
        description="Sanctioned, authorized, or contracted load value."
    )
    sanction_load_unit: Optional[str] = Field(
        None,
        description="Unit of sanctioned load (e.g. kW, HP, kVA)."
    )
    pincode: Optional[str] = Field(
        None,
        description="6-digit postal code of the consumer billing address."
    )
    unit_consumed: Optional[float] = Field(
        None,
        description="Electricity units consumed in this billing cycle (typically kWh or kVAh)."
    )
    rate_per_unit: Optional[float] = Field(
        None,
        description="Average rate charged per unit of electricity."
    )
    bill_date: Optional[str] = Field(
        None,
        description="Issue date of the bill normalized to YYYY-MM-DD format."
    )
    is_combined_bill: bool = Field(
        False,
        description="True if this is a single bill combining multiple months of cycles."
    )
    combined_months_count: int = Field(
        1,
        description="Number of billing months combined in this bill (defaults to 1)."
    )
    detected_language: Optional[str] = Field(
        None,
        description="BCP-47 language code detected or used for digitization."
    )
