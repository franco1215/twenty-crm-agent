import httpx
import json


INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    types {
      name
      kind
      description
      fields {
        name
        description
        type {
          name
          kind
          ofType { name kind ofType { name kind } }
        }
        args {
          name
          type { name kind ofType { name kind } }
        }
      }
    }
  }
}
"""


class TwentyGraphQLClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.endpoint = f"{base_url.rstrip('/')}/api"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    async def execute(
        self, query: str, variables: dict | None = None
    ) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload: dict = {"query": query}
            if variables:
                payload["variables"] = variables
            response = await client.post(
                self.endpoint, json=payload, headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                raise Exception(
                    f"GraphQL errors: {json.dumps(data['errors'], indent=2)}"
                )
            return data.get("data", {})

    async def introspect(self, filter_text: str = "") -> str:
        data = await self.execute(INTROSPECTION_QUERY)
        schema = data.get("__schema", {})
        return self._summarize_schema(schema, filter_text)

    def _summarize_schema(self, schema: dict, filter_text: str = "") -> str:
        lines: list[str] = []
        filter_lower = filter_text.lower()

        query_type = schema.get("queryType", {}).get("name", "Query")
        mutation_type = schema.get("mutationType", {}).get("name", "Mutation")

        for t in schema.get("types", []):
            name = t.get("name", "")
            # Skip internal GraphQL types
            if name.startswith("__"):
                continue
            # Skip scalar/enum types for brevity unless filtered
            if t.get("kind") in ("SCALAR", "ENUM") and not filter_text:
                continue
            # Apply filter
            if filter_text and filter_lower not in name.lower():
                fields = t.get("fields") or []
                field_match = any(
                    filter_lower in (f.get("name", "")).lower() for f in fields
                )
                if not field_match:
                    continue

            kind = t.get("kind", "")
            desc = t.get("description") or ""
            prefix = ""
            if name == query_type:
                prefix = " (QUERIES)"
            elif name == mutation_type:
                prefix = " (MUTATIONS)"

            lines.append(f"\n## {name} [{kind}]{prefix}")
            if desc:
                lines.append(f"  {desc}")

            for field in t.get("fields") or []:
                fname = field.get("name", "")
                if filter_text and filter_lower not in name.lower() and filter_lower not in fname.lower():
                    continue
                ftype = self._format_type(field.get("type", {}))
                fdesc = field.get("description") or ""
                args = field.get("args") or []
                args_str = ""
                if args:
                    arg_parts = [
                        f"{a['name']}: {self._format_type(a.get('type', {}))}"
                        for a in args
                    ]
                    args_str = f"({', '.join(arg_parts)})"
                line = f"  - {fname}{args_str}: {ftype}"
                if fdesc:
                    line += f"  # {fdesc}"
                lines.append(line)

        if not lines:
            return "No types found matching the filter."

        return "\n".join(lines)

    def _format_type(self, type_info: dict) -> str:
        name = type_info.get("name")
        kind = type_info.get("kind")
        of_type = type_info.get("ofType")

        if name:
            return name
        if kind == "NON_NULL" and of_type:
            return f"{self._format_type(of_type)}!"
        if kind == "LIST" and of_type:
            return f"[{self._format_type(of_type)}]"
        return "Unknown"
