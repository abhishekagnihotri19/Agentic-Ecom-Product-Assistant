import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient



async def main():
    client = MultiServerMCPClient(
        {
            "hybrid_search": {
                "command": r"D:\llm_ops\ecomm-prod-assistant\ecommVenv\Scripts\python.exe",
                "args": [
                    "-m",
                    "mcp_servers.product_search_server"    # In args: We have to define path, where exactly server script (product_search_server exist)
                                                           # When specify file name, remeber it should be .exe (product_search_server.exe), and should not be .py(product_search_server.py)
                ],
                "transport": "stdio",  # If we are checking locally, transport would be "stdio"
            # If we are checking on FastAPI Sever than transport would be "http", and apart from "transport", another parameter "url": "http://127.0.0.1:8000", should be mentioned
            }
        }
    )



    # Lets Discover tools
    tools= await client.get_tools()
    print ("Available tools:", [t.name for t in tools])

    #Lets Pick tool by Name
    retriever_tools= next(t for t in tools if t.name=="get_product_info")
    web_tool= next (t for t in tools if t.name=="web_search")


      # --- Step 1: Try retriever first ---
   
    query= "i phone 17"
    retriever_result= await retriever_tools.ainvoke({"query": query})
    print("\nRetriever Result:\n", retriever_result)

    # --- Step 2: Fallback to web search if retriever fails ---
  
# Extract text safely
    retriever_text = ""
    if isinstance(retriever_result, list) and retriever_result:
        retriever_text = retriever_result[0].get("text", "")

    print("\nRetriever Result:\n", retriever_text)

    def is_low_quality(text: str) -> bool:
        if not text.strip():
            return True

        if "Price:N/A" in text and "Rating:N/A" in text:
            return True

        if "Add to Compare" in text:
            return True

        return False
    if is_low_quality(retriever_text):
        web_result = await web_tool.ainvoke({"query": query})
        #web_text = extract_text(web_result)
        #print("\nWeb Search Result:\n", web_text)


    #if not retriever_text.strip() or "No result found" in retriever_text:
        #web_result = await web_tool.ainvoke({"query": query})

       # web_text = ""
        if isinstance(web_result, list) and web_result:
            web_text = web_result[0].get("text", "")

        print("\nWeb Search Result:\n", web_text)

if __name__ == "__main__":
    asyncio.run(main())


# Command to Run this file locally ::::: python -m mcp_servers.client
# HTTP MCP Server Example
# from mcp.server.fastapi import FastAPIMCP
# import uvicorn

# mcp = FastAPIMCP("hybrid_search")

#         | Class        | Transport Type        |
# |       `FastMCP`    | stdio                 |
# |       FastAPIMCP` | HTTP (StreamableHTTP) |

# Command : To Run this FastAPIMCP (HTTP Server file) ::: uvicorn.run(mcp.app)


# async def main():
#     client = MultiServerMCPClient(
#         {
#             "hybrid_search":{
#                 #server name
#                 "args":[
#                     "D:\llm_ops\ecomm-prod-assistant\mcp_servers\product_search_server.py"],
#                 #"args":[r"D:\llm_ops\ecomm-prod-assistant\mcp_servers\product_search_server.exe"],
#                 #"transport": "http",
#                 #"url": "http://127.0.0.1:8000"

#             }
#         }
#     )