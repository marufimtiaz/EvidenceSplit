from evidencesplit.analyses.pipeline import completion_status
from evidencesplit.shared.types import AnalysisStatus


def test_completion_status_uses_warning_terminal_state() -> None:
    assert completion_status(["invalid PDF"]) == AnalysisStatus.COMPLETED_WITH_WARNINGS
    assert completion_status([]) == AnalysisStatus.COMPLETED
