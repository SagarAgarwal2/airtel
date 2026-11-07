"""Smart KYC against the 12 synthetic applicants. Needs Tesseract (or RapidOCR). Run: python -m pytest -q"""
import pytest
from backend import kyc

EXPECTED = {
    "K01": ("manual_review", {"gstin_registry", "udyam_number"}),   # GSTIN cancelled; Udyam number blank
    "K02": ("verified", set()),                                     # tilted scan, straightened
    "K03": ("verified", set()),
    "K04": ("action_needed", {"quality_gst_certificate"}),          # blurry GST certificate
    "K05": ("action_needed", {"present_udyam_certificate"}),        # Udyam certificate missing
    "K06": ("verified", set()),
    "K07": ("manual_review", {"gst_internal"}),                     # legal name vs trade name
    "K08": ("verified", set()),
    "K09": ("verified", set()),
    "K10": ("verified", set()),
    "K11": ("action_needed", {"address_age"}),                      # bill older than 90 days
    "K12": ("verified", set()),
}

pytestmark = pytest.mark.skipif(kyc.ocr_engine() == "none", reason="no OCR engine installed")


@pytest.mark.parametrize("aid", sorted(EXPECTED))
def test_applicant(aid):
    res = kyc.run_case(kyc.analyze_sample(aid))
    status, must_fail = EXPECTED[aid]
    failed = {c["id"] for c in res["checks"] if c["result"] == "fail"}
    assert res["status"] == status, (aid, res["summary"])
    assert must_fail <= failed, (aid, failed)
