"""Combined Kaggle email dataset contract; spam is included in positive labels."""
from typing import Final
SCHEMA_VERSION: Final = "phishing_email_v1"
SOURCE_FILENAME: Final = "phishing_email.csv"
TEXT_COLUMN: Final = "text_combined"
TARGET_COLUMN: Final = "label"
