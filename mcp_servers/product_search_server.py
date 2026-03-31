from mcp.server.fastmcp import FastMCP
from prod_assistant.retriever.retrieval import Retriever
from langchain_community.tools import DuckDuckGoSearchRun

# Initialize MCP Sever
mcp= FastMCP("hybrid_search")
#Loading Retriever

retriever_obj= Retriever()
retriever= retriever_obj.load_retriever()

#Langchain DuckDuckGo Tool

duckduckgo= DuckDuckGoSearchRun()

#------------Helper--------------#
def format_docs(docs)->str:
    if not docs:
        return ""
    formatted_chunks=[]
    for d in docs:
        meta= d.metadata or {}
        formatted= (
            f"Title: {meta.get('product_title', 'N/A')}\n"
            f"Price:{meta.get('price', 'N/A')}\n"
            f"Rating:{meta.get('rating', 'N/A')}\n"
            f"Review:\n{d.page_content.strip()}"

        )
        formatted_chunks.append(formatted)
    return "\n\n----\n\n".join(formatted_chunks)
#product_id,title,price,rating,total_review,top_reviews

#---------------MCP-Tools------#
@mcp.tool()
async def get_product_info(query:str)->str:
        """Retrieve product information for a given query from local retriever."""
        try:
             docs= retriever.invoke(query)
             context= format_docs(docs)
             if not context.strip():
                  return "No local result found"
             return context
        except Exception as e:
             "Error retrieving product info: {str(e)}"

@mcp.tool()
async def web_search (query:str)->str:
    try:
        result = duckduckgo.run(query)
        return result
    
    except Exception as e:
        f"Error during web search: {str(e)}"

        


# ---------- Run Server ----------
if __name__ == "__main__":
    mcp.run(transport="stdio")
   # mcp.run(transport="streamable-http")


# python -m mcp_servers.product_search_server
