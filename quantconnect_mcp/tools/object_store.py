"""Object Store tools: key-value storage shared across an organization's algorithms."""

from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from quantconnect_mcp.client import QuantConnectClient
from quantconnect_mcp.tools._shared import CLIENT, DESTRUCTIVE, MUTATING, READ_ONLY


@tool(annotations=READ_ONLY)
async def list_object_store(
    path: str | None = None,
    organization_id: str | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """List Object Store keys, optionally under a path.

    Args:
        path: Only list keys under this path, for example "models/".
        organization_id: Organization to read. Defaults to your organization.
    """
    return await qc.post(
        "object/list", organizationId=await qc.organization_id(organization_id), path=path
    )


@tool(annotations=READ_ONLY)
async def read_object_store_properties(
    key: str, organization_id: str | None = None, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Read an Object Store entry's metadata: size, modified time, and a content preview.

    Args:
        key: The Object Store key.
        organization_id: Organization to read. Defaults to your organization.
    """
    return await qc.post(
        "object/properties", organizationId=await qc.organization_id(organization_id), key=key
    )


@tool(annotations=READ_ONLY)
async def get_object_store_download(
    keys: list[str] | None = None,
    job_id: str | None = None,
    organization_id: str | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Prepare a download of Object Store entries, in two steps.

    First call with ``keys`` to start a job and get its ``jobId``. Then call with
    that ``job_id`` until the response contains a download ``url``.

    Args:
        keys: Keys to bundle into the download (first step).
        job_id: The job ID returned by the first step (second step).
        organization_id: Organization to read. Defaults to your organization.
    """
    if (keys is None) == (job_id is None):
        raise ToolError("Pass either keys (to start a download) or job_id (to fetch its URL)")
    return await qc.post(
        "object/get",
        organizationId=await qc.organization_id(organization_id),
        keys=keys,
        jobId=job_id,
    )


@tool(annotations=MUTATING)
async def upload_object_store_object(
    key: str,
    content: str,
    organization_id: str | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Write a text value to the Object Store, replacing any existing value at the key.

    Args:
        key: The Object Store key, for example "config/universe.json".
        content: The text to store.
        organization_id: Organization to write to. Defaults to your organization.
    """
    return await qc.upload(
        "object/set",
        fields={"organizationId": await qc.organization_id(organization_id), "key": key},
        files={"objectData": (key.rsplit("/", 1)[-1], content.encode())},
    )


@tool(annotations=DESTRUCTIVE)
async def delete_object_store_object(
    key: str, organization_id: str | None = None, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Delete an Object Store entry.

    Args:
        key: The Object Store key to delete.
        organization_id: Organization to delete from. Defaults to your organization.
    """
    return await qc.post(
        "object/delete", organizationId=await qc.organization_id(organization_id), key=key
    )


TOOLS = (
    list_object_store,
    read_object_store_properties,
    get_object_store_download,
    upload_object_store_object,
    delete_object_store_object,
)
