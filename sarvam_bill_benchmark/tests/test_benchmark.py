import unittest
from unittest.mock import MagicMock
from app.models.extraction import BillExtractionResult
from app.services.extraction_service import ExtractionService

class TestBenchmarkExtractor(unittest.TestCase):
    
    def setUp(self):
        self.mock_client = MagicMock()
        self.service = ExtractionService(self.mock_client)

    def test_clean_ocr_text_base64_removal(self):
        sample_markdown = """# Electric Bill
![Image](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyBAMAAADtQTY9AAAAGFBMVEUAAAD///8A...)
Some text content here.
<img src="data:image/jpeg;base64,AABBAAC..." />
More text.
"""
        cleaned = self.service._clean_ocr_text(sample_markdown)
        self.assertNotIn("data:image/png;base64", cleaned)
        self.assertNotIn("data:image/jpeg;base64", cleaned)
        self.assertIn("[IMAGE]", cleaned)
        self.assertIn("Some text content here.", cleaned)

    def test_clean_json_content(self):
        raw_output = """
        Some conversation text...
        ```json
        {
          "document_type_match": true,
          "discom": "MSEDCL",
          "consumer_number": "279950083331",
          "total_bill_amount": 1050.0,
          "bill_amount": 1050.0,
          "arrears": 0.0,
          "overdue_months_count": null,
          "name": "AMIT ARVIND MALEKAR",
          "fathers_name": null,
          "address": "NO 334 PLOT 86 AHILA NAGAR KUPWAD 416425",
          "sanction_load": 5.0,
          "sanction_load_unit": "kW",
          "pincode": "416425",
          "unit_consumed": 120.0,
          "rate_per_unit": 6.8,
          "bill_date": "2026-06-06",
          "is_combined_bill": false,
          "combined_months_count": 1
        }
        ```
        Some trailing conversation.
        """
        cleaned = self.service._clean_json_content(raw_output)
        self.assertTrue(cleaned.startswith("{"))
        self.assertTrue(cleaned.endswith("}"))

    def test_pydantic_validation_success(self):
        valid_json = """{
          "document_type_match": true,
          "discom": "BESCOM",
          "consumer_number": "987654321",
          "total_bill_amount": 2500.0,
          "bill_amount": 2500.0,
          "arrears": 0.0,
          "overdue_months_count": null,
          "name": "John Doe",
          "fathers_name": null,
          "address": "456 Park Rd, Bangalore",
          "sanction_load": 3.0,
          "sanction_load_unit": "kW",
          "pincode": "560001",
          "unit_consumed": 410.0,
          "rate_per_unit": null,
          "bill_date": "2026-06-01",
          "is_combined_bill": false,
          "combined_months_count": 1
        }"""
        result = self.service._parse_and_validate(valid_json)
        self.assertIsInstance(result, BillExtractionResult)
        self.assertEqual(result.discom, "BESCOM")
        self.assertEqual(result.total_bill_amount, 2500.0)
        self.assertEqual(result.is_combined_bill, False)

    def test_pydantic_validation_error(self):
        # Missing required field document_type_match
        invalid_json = """{
          "discom": "BESCOM"
        }"""
        with self.assertRaises(ValueError):
            self.service._parse_and_validate(invalid_json)

    def test_post_process_extracted_data(self):
        # Sample dict with various edge cases
        raw_data = {
            "name": "MR. VIJAY KUMARSIO Mr. KASHMIRI LAL",
            "fathers_name": None,
            "consumer_number": "MR. VIJAY KUMAR",  # name match
            "sanction_load": 594.0,
            "sanction_load_unit": "kVAh",  # unit consumed unit
            "pincode": "60021347848",  # invalid length pincode
            "address": "Some street, UNNAO - 209801"
        }
        processed = self.service._post_process_extracted_data(raw_data)
        self.assertEqual(processed["name"], "MR. VIJAY KUMAR")
        self.assertEqual(processed["fathers_name"], "Mr. KASHMIRI LAL")
        self.assertIsNone(processed["consumer_number"])
        self.assertIsNone(processed["sanction_load"])
        self.assertIsNone(processed["sanction_load_unit"])
        self.assertEqual(processed["pincode"], "209801")

if __name__ == '__main__':
    unittest.main()
