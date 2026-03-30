"""Basic tests for the GraphQL client (run with Twenty CRM available)."""

import asyncio
import os
import pytest

# Skip all tests if Twenty CRM is not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("TWENTY_API_KEY"),
    reason="TWENTY_API_KEY not set — skip integration tests",
)


@pytest.fixture
def client():
    from src.graphql_client import TwentyGraphQLClient

    return TwentyGraphQLClient(
        base_url=os.getenv("TWENTY_CRM_URL", "http://localhost:3000"),
        api_key=os.getenv("TWENTY_API_KEY", ""),
    )


@pytest.mark.asyncio
async def test_introspect_returns_schema(client):
    result = await client.introspect()
    assert isinstance(result, str)
    assert len(result) > 100
    # Should contain some Twenty CRM types
    assert "Query" in result or "Mutation" in result or "company" in result.lower()


@pytest.mark.asyncio
async def test_introspect_with_filter(client):
    result = await client.introspect("company")
    assert isinstance(result, str)
    assert "company" in result.lower() or "Company" in result


@pytest.mark.asyncio
async def test_query_companies(client):
    result = await client.execute("""
        query {
            companies(first: 3) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """)
    assert "companies" in result
    assert "edges" in result["companies"]


@pytest.mark.asyncio
async def test_query_with_error(client):
    with pytest.raises(Exception, match="GraphQL errors"):
        await client.execute("{ nonExistentField }")
