import asyncio
import json
import shlex
import sys
from typing import List, Dict, Any, Optional
from ChatOpenAI import ChatOpenAI
from MCPClient import MCPClient

class Agent:
    def __init__(self,
                 model: str = "",
                 mcp_clients: List[MCPClient] = [],
                 system_prompt: str = "",
                 context: str = ""):
        """
        Args:
            model: The model to use for the LLM
            mcp_clients: The MCP clients to use for the agent
            system_prompt: The system prompt to use for the agent
            context: The context to use for the agent
        """

        self.model = model
        self.mcp_clients = mcp_clients
        self.system_prompt = system_prompt
        self.context = context
        self.llm: Optional[ChatOpenAI] = None

    async def init(self):
        """
        Agent initialization
        """

        tools = []

        # Initialize tools
        for mcp_client in self.mcp_clients:
            for tool in mcp_client.get_tools():
                tools.append(tool)

        # Initialize LLM
        self.llm = ChatOpenAI(
            self.model,
            self.system_prompt,
            tools,
            self.context
        )

    async def close(self):
        """
        Close the agent
        """

        for mcp_client in self.mcp_clients:
            try:
                await mcp_client.close()
            except Exception as e:
                print(f"关闭MCP客户端时出错: {e}，继续关闭其他客户端")

    async def invoke(self, prompt: str):
        """
        Agent workflow
        """

        if not self.llm:
            raise ValueError("LLM not initialized")
        
        # 根据系统提示词和上下文，生成初始prompt，会包括当前agent注册了哪些mcp server
        # 就类似cursor，cline中的mcp.json
        # 可以让大模型知道自己可以调用哪些mcp server
        response = await self.llm.chat(prompt)

        echo = 0
        while True:
            print(f"======================echo: {echo}=======================")
            echo += 1

            if response["tool_calls"]:
                for tool_call in response["tool_calls"]:
                    print("======================tool_call: =======================")
                    print(f"{tool_call}")

                    # 根据tool_call，找到对应的mcp client
                    client: MCPClient | None = None
                    for mcp_client in self.mcp_clients:
                        tools = mcp_client.get_tools()
                        for tool in tools:
                            if tool.name == tool_call.function.name:
                                client = mcp_client
                                break

                    if client:
                        # 调用mcp server的工具，并返回结果
                        result = await client.call_tool(
                            tool_call.function.name,
                            json.loads(tool_call.function.arguments)
                        )
                        # Convert the result to a serializable format before using json.dumps
                        result_dict = {"result": str(result)}
                        print(f"=========result: {json.dumps(result_dict)}===========")

                        # 将结果返回给llm
                        self.llm.append_tool_result(
                            tool_call.id,
                            json.dumps(result_dict["result"])
                        )
                    else:
                        self.llm.append_tool_result(
                            tool_call.id,
                            "Tool not found"
                        )

                # 再次调用llm
                response = await self.llm.chat()
                continue
            else:
                return {
                    "content": response["content"],
                    "tool_calls": response["tool_calls"] if "tool_calls" in response else [],
                }


async def example() -> None:
    enabled_mcp_clients = []
    agent = None
    try:
        for mcp_tool, cmd in [
            ("fetch", "uvx mcp-server-fetch"),
            ("person", "python src/MCPServer.py"),
        ]:
            try:
                command, *args = shlex.split(cmd)

                mcp_client = MCPClient(
                    name=mcp_tool,
                    command=command,
                    args=args,
                )
                enabled_mcp_clients.append(mcp_client)

                await mcp_client.init()
                tools = mcp_client.get_tools()
                print(tools)
            except Exception as e:
                print(f"初始化 {mcp_tool} 客户端时出错: {e}，跳过此客户端")

        if not enabled_mcp_clients:
            print("警告: 没有任何MCP客户端初始化成功")
            return

        agent = Agent(
            model="deepseek/deepseek-chat-v3-0324",
            mcp_clients=enabled_mcp_clients,
            system_prompt="回答之前先叫一声龙哥好！你可以使用person服务的my_mcp_server工具来获取人物信息，只需要提供名字即可。"
        )
        await agent.init()

        res = await agent.invoke(
            "龙哥，你能告诉我关于张三这个人的信息吗？使用person服务的my_mcp_server工具查询。之后在帮我爬取 https://sports.qq.com 网站的NBA最近发生的大事件，并用中文告诉我。在帮我上网查一下马猴烧酒是啥意思，还有114514是啥意思"
        )

        sys.exit(0)

    except Exception as e:
        print(f"Error during agent execution: {e!s}")
    finally:
        if agent:
            try:
                await agent.close()
            except Exception as e:
                print(f"关闭Agent时出错: {e}")


if __name__ == "__main__":
    asyncio.run(example())        