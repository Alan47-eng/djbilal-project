from typing import TypeAlias

JSONValue: TypeAlias = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]


def normalize_json_value(value: object) -> JSONValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        return {key: normalize_json_value(item) for key, item in value.items()}
    raise ValueError("Value is not JSON serializable")


def parse_json_object(raw_body: bytes) -> JSONObject:
    import json

    value: object = json.loads(raw_body)
    normalized = normalize_json_value(value)
    if not isinstance(normalized, dict):
        raise ValueError("Expected a JSON object")
    return normalized
