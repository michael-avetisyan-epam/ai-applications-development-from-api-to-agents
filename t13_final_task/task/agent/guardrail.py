import logging

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.predefined_recognizers import CreditCardRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)

_REDACTED = "***"
_NLP_CONFIG = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}


class _UMSCreditCardRecognizer(CreditCardRecognizer):
    """
    Extends Presidio's built-in CreditCardRecognizer to bypass Luhn validation.

    UMS generates fake/test card numbers that fail the Luhn checksum. The parent's
    validate_result() would silently drop every match by setting score to 0.0.
    This subclass overrides validate_result() to return None and supplies UMS-specific
    patterns while inheriting context words and language support from the parent.
    """

    CONTEXT = CreditCardRecognizer.CONTEXT

    def validate_result(self, pattern_text: str) -> None:
        return None

    def __init__(self):
        ums_patterns = [
            Pattern(
                name="card_num_pydict",
                regex=r"(?<='num': ')\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}(?=')",
                score=0.95,
            ),
            Pattern(
                name="card_num_json",
                regex=r'(?<="num": ")\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}(?=")',
                score=0.95,
            ),
            Pattern(
                name="card_num_standalone",
                regex=r"\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b",
                score=0.85,
            ),
            Pattern(
                name="card_cvv_pydict",
                regex=r"(?<='cvv': ')\d{3,4}(?=')",
                score=0.95,
            ),
            Pattern(
                name="card_cvv_json",
                regex=r'(?<="cvv": ")\d{3,4}(?=")',
                score=0.95,
            ),
            Pattern(
                name="card_exp_pydict",
                regex=r"(?<='exp_date': ')\d{2}/\d{4}(?=')",
                score=0.95,
            ),
            Pattern(
                name="card_exp_json",
                regex=r'(?<="exp_date": ")\d{2}/\d{4}(?=")',
                score=0.95,
            ),
        ]
        super().__init__(patterns=ums_patterns)


class _UMSSalaryRecognizer(PatternRecognizer):
    """Detects salary values in YAML-like, JSON, Python-dict, and plain-text formats."""

    def __init__(self):
        super().__init__(
            supported_entity="SALARY",
            patterns=[
                Pattern(
                    name="salary_yaml",
                    regex=r"(?<=salary: )\d[\d,]*(?:\.\d+)?",
                    score=0.9,
                ),
                Pattern(
                    name="salary_json",
                    regex=r'(?<="salary": )\d[\d,]*(?:\.\d+)?',
                    score=0.9,
                ),
                Pattern(
                    name="salary_pydict",
                    regex=r"(?<='salary': )\d[\d,]*(?:\.\d+)?",
                    score=0.9,
                ),
                Pattern(
                    name="salary_text_currency",
                    regex=r"(?i)(?<=salary: )\$?[\d,]+(?:\.\d+)?",
                    score=0.85,
                ),
            ],
        )


class UMSDataGuardrail:
    """
    Redacts credit card numbers (num, cvv) and salary values from UMS tool results.
    """

    _ENTITIES = ["CREDIT_CARD", "SALARY"]
    _OPERATORS = {
        "CREDIT_CARD": OperatorConfig("replace", {"new_value": _REDACTED}),
        "SALARY": OperatorConfig("replace", {"new_value": _REDACTED}),
    }

    def __init__(self):
        self.analyzer = self._build_analyzer()
        self.anonymizer = AnonymizerEngine()
        logger.info("UMSDataGuardrail initialized")

    @staticmethod
    def _build_analyzer() -> AnalyzerEngine:
        provider = NlpEngineProvider(nlp_configuration=_NLP_CONFIG)
        nlp_engine = provider.create_engine()
        analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        analyzer.registry.add_recognizer(_UMSCreditCardRecognizer())
        analyzer.registry.add_recognizer(_UMSSalaryRecognizer())
        return analyzer

    def redact(self, text: str) -> str:
        results = self.analyzer.analyze(text=text, language="en", entities=self._ENTITIES)
        if not results:
            return text

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=self._OPERATORS,
        )
        return anonymized.text
