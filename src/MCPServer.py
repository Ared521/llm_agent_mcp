from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp server")

@mcp.tool()
def my_mcp_server(input: str) -> dict:
    """
    明确说明了 输入的input 是什么样的一个人

    args:
        input: 这个人的名字

    returns:
        the result
    """

    return input + " 是一个阳光帅气开朗的大男孩"

# 添加入口点，使其可以直接运行
if __name__ == "__main__":
    print("MCP服务器启动中...")
    mcp.run(transport="stdio")

