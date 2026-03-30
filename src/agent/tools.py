from langchain_core.tools import tool
from src.graphql_client import TwentyGraphQLClient
from src.config import config

_client = TwentyGraphQLClient(config.twenty_crm_url, config.twenty_api_key)


@tool
async def introspect_schema(filter: str = "") -> str:
    """Discover the Twenty CRM GraphQL schema. Returns available types, queries, and mutations.
    Use this FIRST before writing any query to learn the correct field names and types.

    Args:
        filter: Optional filter to search for specific types or fields by name substring.
    """
    return await _client.introspect(filter)


@tool
async def query_graphql(query: str, variables: str = "{}") -> str:
    """Execute a read-only GraphQL query against Twenty CRM.
    Use introspect_schema first to understand the available schema.

    Args:
        query: The GraphQL query string.
        variables: JSON string of query variables (default: "{}").
    """
    import json

    vars_dict = json.loads(variables) if variables and variables != "{}" else None
    result = await _client.execute(query, vars_dict)
    return json.dumps(result, indent=2, default=str)


@tool
async def mutate_graphql(operation: str, query: str, variables: str = "{}") -> str:
    """Execute a GraphQL mutation (create, update, or delete) against Twenty CRM.
    This requires user approval before execution.

    Args:
        operation: Human-readable description of what this mutation does (e.g., "Create company Acme Corp").
        query: The GraphQL mutation string.
        variables: JSON string of mutation variables (default: "{}").
    """
    import json

    vars_dict = json.loads(variables) if variables and variables != "{}" else None
    result = await _client.execute(query, vars_dict)
    return json.dumps(result, indent=2, default=str)


ALL_TOOLS = [introspect_schema, query_graphql, mutate_graphql]
READ_TOOLS = {introspect_schema.name, query_graphql.name}
WRITE_TOOLS = {mutate_graphql.name}
