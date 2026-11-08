"""Cliente MCP mínimo: sobe o servidor via stdio, lista e chama tools.

Faz o mesmo que o Claude Desktop: initialize -> tools/list -> tools/call.
(`print` aqui é permitido: este script é o cliente, não o servidor.)
"""
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PARAMS = StdioServerParameters(command="uv", args=["run", "dados-br-mcp"])


async def main() -> None:
    async with stdio_client(PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools disponíveis:")
            for t in tools.tools:
                print(f"  - {t.name}")

            ok = await session.call_tool("ultimos_valores", {"serie": "ipca", "n": 3})
            print("\nultimos_valores(ipca, 3):", ok.content[0].text)

            # No SDK mcp 2.x os campos são snake_case: is_error (no protocolo, isError).
            erro = await session.call_tool("ultimos_valores", {"serie": "inflacao"})
            print("\nerro esperado -> isError =", erro.is_error)
            print(erro.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
