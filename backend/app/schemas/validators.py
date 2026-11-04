from typing import Any

from pydantic import AnyHttpUrl, TypeAdapter

http_url_adapter = TypeAdapter(AnyHttpUrl)


def validate_http_url(value: Any) -> Any:
    if value is None:
        return None
    return str(http_url_adapter.validate_python(value))
