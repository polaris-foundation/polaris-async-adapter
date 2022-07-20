from datetime import datetime, timezone
from typing import Dict, List, Union

from marshmallow import INCLUDE, Schema

from dhos_async_adapter import config


class ExportMessage(Schema):
    """No validation required for this message type."""

    class Meta:
        unknown = INCLUDE


def generate_dea_ingest_payload(
    export_data: Union[Dict, List[Dict]], data_type: str
) -> Dict:
    return {
        "metadata": {
            "data_source": __name__,
            "data_type": data_type,
            "customer": config.CUSTOMER_CODE,
            "environment": config.ENVIRONMENT,
            "circle_tag": config.BUILD_CIRCLE_TAG,
            "git_tag": config.BUILD_GIT_TAG,
            "created": datetime.now(timezone.utc).isoformat(),
            "num_records": len(export_data),
        },
        "data": export_data,
    }
