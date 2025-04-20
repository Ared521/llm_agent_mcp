from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp server")

@mcp.tool()
def my_mcp_server(input: str) -> dict:
    """
    说明了输入的 input 是一个怎样的人

    args:
        input: 这个人的名字

    returns:
        the result
    """
    
    return input + " 是一个阳光帅气开朗的大男孩"

# 添加入口点，使其可以直接运行
if __name__ == "__main__":
    mcp.run(transport="stdio")