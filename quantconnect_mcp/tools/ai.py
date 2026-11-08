"""QuantConnect's AI coding tools: syntax checks, error help, search, and completion."""

from typing import Annotated, Any, Literal

from fastmcp.tools import tool
from pydantic import Field

from quantconnect_mcp.client import QuantConnectClient
from quantconnect_mcp.tools._shared import CLIENT, READ_ONLY, CodeFile, Language

SearchSource = Literal["Docs", "Examples", "Stubs", "Forum"]


def _files(files: list[CodeFile]) -> list[dict[str, Any]]:
    return [file.to_api() for file in files]


@tool(annotations=READ_ONLY)
async def check_syntax(
    files: list[CodeFile], language: Language = "Py", qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Check algorithm code for syntax and API errors without compiling a project.

    Args:
        files: The files to check.
        language: "Py" for Python or "C#".
    """
    return await qc.post("ai/tools/syntax-check", language=language, files=_files(files))


@tool(annotations=READ_ONLY)
async def initialize_backtest(
    files: list[CodeFile], language: Language = "Py", qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Run an algorithm for a few seconds to surface initialization errors.

    Args:
        files: The algorithm files. One must be main.py (Python) or Main.cs (C#).
        language: "Py" for Python or "C#".
    """
    return await qc.post("ai/tools/backtest-init", language=language, files=_files(files))


@tool(annotations=READ_ONLY)
async def enhance_error(
    message: str,
    stacktrace: str | None = None,
    language: Language = "Py",
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Explain a LEAN compile or runtime error and suggest fixes.

    Args:
        message: The error message.
        stacktrace: The stack trace, if available.
        language: "Py" for Python or "C#".
    """
    error = {"message": message, "stacktrace": stacktrace}
    return await qc.post(
        "ai/tools/error-enhance",
        language=language,
        error={key: value for key, value in error.items() if value is not None},
    )


@tool(annotations=READ_ONLY)
async def search_quantconnect(
    query: str,
    sources: list[SearchSource] | None = None,
    count: Annotated[int, Field(ge=1, le=25)] = 5,
    language: Language = "Py",
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Search QuantConnect documentation, examples, API stubs, and forum posts.

    Args:
        query: What to search for, for example "How to create an Alpha model".
        sources: Where to search. Defaults to Docs and Examples.
        count: Results to return from each source.
        language: "Py" for Python or "C#".
    """
    criteria = [
        {"input": query, "type": source, "count": count}
        for source in sources or ("Docs", "Examples")
    ]
    return await qc.post("ai/tools/search", language=language, criteria=criteria)


@tool(annotations=READ_ONLY)
async def complete_code(
    sentence: str,
    language: Language = "Py",
    response_size_limit: int | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Suggest LEAN API completions for a partial expression, for example "self.add_eq".

    Args:
        sentence: The partial code to complete.
        language: "Py" for Python or "C#".
        response_size_limit: Maximum number of suggestions.
    """
    return await qc.post(
        "ai/tools/complete",
        language=language,
        sentence=sentence,
        responseSizeLimit=response_size_limit,
    )


@tool(annotations=READ_ONLY)
async def convert_to_pep8(files: list[CodeFile], qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """Rewrite Python algorithm code from the legacy PascalCase API to PEP 8 snake_case.

    Args:
        files: The Python files to convert.
    """
    return await qc.post("ai/tools/pep8-convert", files=_files(files))


TOOLS = (
    check_syntax,
    initialize_backtest,
    enhance_error,
    search_quantconnect,
    complete_code,
    convert_to_pep8,
)
