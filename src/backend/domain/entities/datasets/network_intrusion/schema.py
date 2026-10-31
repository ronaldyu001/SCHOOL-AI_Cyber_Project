"""Fixed ToN_IoT binary-classification contract from the confirmed notebook.

Order within each feature group is part of the TabM checkpoint contract.
"""
from enum import IntEnum
from typing import Final

class NetworkIntrusionLabel(IntEnum):
    NORMAL = 0
    ATTACK = 1

SCHEMA_VERSION: Final = "ton_iot_binary_v1"
SOURCE_FILENAME: Final = "train_test_network.csv"
TARGET_COLUMN: Final = "label"
MISSING_TOKEN: Final = "-"
NUMERIC_FEATURES: Final = ('src_port', 'dst_port', 'duration', 'src_bytes', 'dst_bytes', 'missed_bytes', 'src_pkts', 'src_ip_bytes', 'dst_pkts', 'dst_ip_bytes', 'dns_qclass', 'dns_qtype', 'dns_rcode', 'http_request_body_len', 'http_response_body_len', 'http_status_code')
CATEGORICAL_FEATURES: Final = ('src_ip', 'dst_ip', 'proto', 'service', 'conn_state')
EXCLUDED_FEATURES: Final = (
    "dns_query", "dns_AA", "dns_RD", "dns_RA", "dns_rejected",
    "ssl_version", "ssl_cipher", "ssl_resumed", "ssl_established",
    "ssl_subject", "ssl_issuer", "http_trans_depth", "http_method",
    "http_uri", "http_version", "http_user_agent", "http_orig_mime_types",
    "http_resp_mime_types", "weird_name", "weird_addl", "weird_notice", "type",
)
# The notebook dropped these columns at >=80% missingness, then dropped type.
# Use this fixed selection at runtime rather than recomputing the schema.
UNKNOWN_CATEGORY_ID: Final = 0
MISSING_CATEGORY_ID: Final = 1


def validate_feature_order(numeric: tuple[str, ...], categorical: tuple[str, ...]) -> None:
    if numeric != NUMERIC_FEATURES or categorical != CATEGORICAL_FEATURES:
        raise ValueError("Feature order does not match " + SCHEMA_VERSION)
