import asyncio
from typing import Any, Optional
from contextlib import AsyncExitStack
import shlex
from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client

from rich import print as rprint

from dotenv import load_dotenv

load_dotenv()


class MCPClient:
    def __init__(
        self,
        name: str,
        command: str,
        args: list[str],
        version: str = "0.0.1",
    ) -> None:
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.name = name
        self.version = version
        self.command = command
        self.args = args
        self.tools: list[Tool] = []

    async def init(self) -> None:
        await self.connect_to_server()

    async def close(self) -> None:
        try:
            try:
                await self.exit_stack.aclose()
            except asyncio.CancelledError:
                # 忽略cancel错误，这通常发生在尝试关闭子进程时
                print("")
            except Exception:
                # Error during MCP client close, traceback and continue!
                rprint("")
        except Exception as e:
            # f"关闭MCP客户端时出现其他错误: {str(e)}"
            print("")

    def get_tools(self) -> list[Tool]:
        return self.tools

    async def connect_to_server(self) -> None:
        """
        Connect to an MCP server
        """

        server_params = StdioServerParameters(
            command = self.command,
            args = self.args,
            env = None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params),
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        self.tools = response.tools

        print("\nConnected to server with tools:", [tool.name for tool in self.tools])
        print("==================== tool lists ======================")
        print(response)

    # 调用mcp server的工具，并返回结果
    async def call_tool(self, name: str, params: dict[str, Any]):
        return await self.session.call_tool(name, params)


async def example() -> None:
    clients = []
    for mcp_tool, cmd in [
        ("fetch", "uvx mcp-server-fetch")
    ]:
        
        command, *args = shlex.split(cmd)

        mcp_client = MCPClient(
            name=command,
            command=command,
            args=args,
        )
        clients.append(mcp_client)

        await mcp_client.init()
        tools = mcp_client.get_tools()
        rprint(tools)
        await mcp_client.close()


if __name__ == "__main__":
    asyncio.run(example())
