"""Numeric database IDs are serialized as strings for the existing web client."""

from fastapi.responses import JSONResponse


def public_ids(value, key=""):
    if isinstance(value, dict):
        return {k: public_ids(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [public_ids(v, key[:-1] if key.endswith("_ids") else "") for v in value]
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and (key == "id" or key.endswith("_id"))
    ):
        return str(value)
    return value


class PublicJSONResponse(JSONResponse):
    def render(self, content):
        return super().render(public_ids(content))
