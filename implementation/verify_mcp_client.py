from __future__ import annotations

import asyncio
from pathlib import Path

from fastmcp import Client

from init_db import create_database


async def main() -> None:
    create_database()
    server_path = Path(__file__).with_name('mcp_server.py')
    async with Client(str(server_path)) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()

        print('tools:', [tool.name for tool in tools])
        print('resources:', [str(resource.uri) for resource in resources])
        print('resource_templates:', [str(template.uriTemplate) for template in templates])

        search_result = await client.call_tool(
            'search',
            {'table': 'students', 'filters': {'cohort': 'A1'}, 'limit': 2},
        )
        print('search result:', search_result.data)

        schema_result = await client.read_resource('schema://database')
        table_schema_result = await client.read_resource('schema://table/students')
        print('schema resource items:', len(schema_result))
        print('table schema resource items:', len(table_schema_result))


if __name__ == '__main__':
    asyncio.run(main())

