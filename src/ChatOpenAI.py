import os
import asyncio
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI, NOT_GIVEN
from mcp import Tool

from dotenv import load_dotenv
from pydantic import BaseModel
from rich import print as rprint

load_dotenv()

class tool_call_function(BaseModel):
    name: str = ""
    arguments: str = ""


class tool_call(BaseModel):
    id: str = ""
    function: tool_call_function = tool_call_function()

class ChatOpenAI:
    def __init__(self,
                 model: str,
                 system_prompt: str = "",
                 tools: List[Tool] = [],
                 context: str = ""):
        
        self.llm = AsyncOpenAI(
            api_key = os.getenv("OPENAI_API_KEY"),
            base_url = os.getenv("OPENAI_BASE_URL"),
        )
        self.model = model
        self.tools = tools
        self.messages = []

        if system_prompt:
            self.messages.append({
                "role": "system",
                "content": system_prompt
            })

        if context:
            self.messages.append({
                "role": "user",
                "content": context
            })

    async def chat(self, prompt: str = ""):
        print("========================chatting...=========================")
        
        if (prompt):
            self.messages.append({
                "role": "user",
                "content": prompt
            })

        content = []
        tool_calls = []
        
        print("========================response...=========================")
        async with await self.llm.chat.completions.create(
            model = self.model,
            messages = self.messages,
            tools = self.get_tools_definition(),
            stream = True
        ) as stream:
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    content_chunk = delta.content
                    content.append(content_chunk)
                    rprint(content_chunk, end='', flush=True)
            
                if delta.tool_calls:
                    for tool_call_chunk in delta.tool_calls:
                        if len(tool_calls) <= tool_call_chunk.index:
                            tool_calls.append(tool_call())

                        cur_tool_call = tool_calls[tool_call_chunk.index]

                        if tool_call_chunk.id:  
                            cur_tool_call.id += tool_call_chunk.id
                        if tool_call_chunk.function:
                            if tool_call_chunk.function.name:   
                                cur_tool_call.function.name += tool_call_chunk.function.name
                            if tool_call_chunk.function.arguments:
                                cur_tool_call.function.arguments += tool_call_chunk.function.arguments
                    

        self.messages.append({
            "role": "assistant",
            "content": content,
            # 需要符合 OpenAI API chat completion message的asstiant的格式
            "tool_calls": [{
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
            } for tool_call in tool_calls]
        })

        return {
            "content": content,
            "tool_calls": tool_calls
        }      
    
    # 外部调用完工具，把结果返回给llm
    def append_tool_result(self, tool_call_id: str, tool_result: str):
        self.messages.append({
            "role": "tool",
            "content": tool_result,
            "tool_call_id": tool_call_id
        })

    def get_tools_definition(self):
        """
        生成 (OpenAI API格式) 的工具定义结构
        """
        
        if not self.tools:
            return []
        
        return [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in self.tools]
    
if __name__ == "__main__":
    llm = ChatOpenAI(
        model="gpt-4o",
        system_prompt="你是一个AI助手，可以回答用户的问题。回答之前先叫一声龙哥好！"
    )

    asyncio.run(llm.chat(prompt='你好'))
           
