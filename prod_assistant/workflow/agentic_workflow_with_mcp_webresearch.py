from typing import Annotated,Sequence, Literal,List,TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from prod_assistant.prompt_library.prompts import PromptRegistry, PromptType
from prod_assistant.retriever.retrieval import Retriever
from prod_assistant.utils.model_loader import ModelLoader
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
import uuid
import os

class AgenticRAG:
    """Agentic RAG Pipeling using MCP Server"""
    async def initialize(self):
        try:
            print("🔄 Fetching MCP tools...")
            self.mcp_tools = await self.mcp_client.get_tools()
            print("✅ MCP tools loaded:", [t.name for t in self.mcp_tools])

        except Exception as e:
            import traceback
            print("❌ FULL MCP ERROR ↓↓↓")
            traceback.print_exc()
            self.mcp_tools = []

    class AgentState(TypedDict, total=False):
        # total= False, meaning following total variable are optional, not Mandatory
        
        messages: Annotated[Sequence[BaseMessage], add_messages]
        #Following variable are defined as State
        question: str
        query:str
        context: str
        needs_retrieval:bool
        answer:str

    def __init__(self):
       self.retrieval_obj= Retriever()
       self.retriever= self.retrieval_obj.load_retriever()
       load_model= ModelLoader()
       self.llm= load_model.load_llm()
       self.checkpointer= MemorySaver()

       self.mcp_client= MultiServerMCPClient(
           {
               "hybrid_search":{
                   "transport":"streamable_http",
                   "url": os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp")

               }
           }
           
       )

       self.mcp_tools=[] # Safe default fallback
        #Build WORKFLOW
       self.workflow=self.build_workflow()
       self.app= self.workflow.compile(checkpointer=self.checkpointer)


    # Load MCP tools Asychronously


    async def initialize(self):
        try:
            self.mcp_tools= await self.mcp_client.get_tools()
            print ("MCP tools loaded")
        except Exception as e:
            print(f"⚠ Warning: Failed to load MCP tools — {e}")
            self.mcp_tools=[]

    def entry_state(self, state:AgentState):
        print ("---ENtry State-----")
        question= state["messages"][-1].content 
        return {"question": question}


    def ai_assistant(self, state: AgentState):
        print ("----AI Assistant Starts-----")
        question= state['question']
        keywords =['price', 'review', 'product']
        needs_retrieval= any (k in question.lower() for k in keywords)
        if needs_retrieval:
            return{
                "query": question,
                "needs_retrieval": True
            }
        #   Direct Answer bu LLM if retriever not required

        prompt= ChatPromptTemplate.from_template("You are helpful Assistant , \n Answer the question directly {question} \nAnswer:")
        chain= prompt | self.llm | StrOutputParser()
        response= chain.invoke({"question":question})
        print ("LLM response:", response)
        return{
            "needs_retrieval": False,
            "answer": response,
            "messages":[AIMessage(content= response)]}
    
    async def vector_retriever(self, state:AgentState):
        print ("----Vector Data Base Starting-----")

        query= state["query"]

       # In Simple Agentic RAG or Vanilla RAG we are Exposing Retriver like this  
       # [retrieved= self.retrieval_obj.call_retriever(query)] 

       # But Here, we are Exposing our tools in MCP server and Call from there
        tool = next ((t for t in self.mcp_tools if t.name == "get_product_info"), None)

        if not tool:
            return {"messages": [AIMessage(content =" Retriever tool not found in MCP Client")]}
        try:
            result= await tool.ainvoke({"query": query})
            context= result or "No relevant Data Found"
            return  {"context":context}
        
        except Exception as e:
            context= f"Error during invoking Retriever:{e}"
            return {"context":context}
    

    async def web_search(self, state: AgentState):
        query = state["query"]

        tool_web = next((t for t in self.mcp_tools if t.name == "web_search"), None)

        if not tool_web:
            return {"context": "Web search not available"}

        try:
            result = await tool_web.ainvoke({"query": query})

            print("🌐 WebSearch Result:", result)

            context = str(result) if result else "No web data found"

            # ✅ FORCE OVERRIDE STATE
            return {
                "context": context,
                "messages": [AIMessage(content=context)]  # 🔥 VERY IMPORTANT
            }

        except Exception as e:
            return {
                "context": f"Web search error: {str(e)}"
            }
        

    
    def _route_after_assistant(self, state:AgentState):
        if state.get("needs_retrieval"):
          return "Retriever"
        return END
    
    def generator(self, state: AgentState):
        context = state.get("context", "")
        
        # 🔥 HANDLE MCP STRUCTURE
        if isinstance(context, list):
            context = " ".join([c.get("text", "") for c in context if isinstance(c, dict)])

        context = str(context)

        print("🧠 FINAL CONTEXT:", context)

        question = state.get("question", "")

        template_str = PromptRegistry[PromptType.PRODUCT_BOT].template
        prompt = ChatPromptTemplate.from_template(template_str)

        chain = prompt | self.llm | StrOutputParser()

        gen_response = chain.invoke({
            "question": question,
            "context": context
        })

        return {
            "answer": gen_response,
            "messages": [AIMessage(content=gen_response)],
        }
    def _route_after_retriever(self, state: AgentState):
        context = state.get("context", "")

        context_str = str(context).lower()

        print("🔍 Context:", context_str)

        if (
            not context
            or "n/a" in context_str
            or "not available" in context_str
            or "no data" in context_str
        ):
            print("⚠️ Routing to WebSearch")
            return "WebSearch"   

        print("✅ Routing to Generator")
        return "Generator"       
# Build Workflow

    def build_workflow(self):
        workflow= StateGraph(self.AgentState)
        workflow.add_node("Entry", self.entry_state)
        workflow.add_node("Assistant", self.ai_assistant)
        workflow.add_node ("Retriever", self.vector_retriever)
        workflow.add_node("Generator", self.generator)
        workflow.add_node("WebSearch", self.web_search)

        workflow.add_edge(START, "Entry")

        workflow.add_edge ("Entry", "Assistant")
        workflow.add_conditional_edges("Assistant", self._route_after_assistant,
                                       {
            "Retriever":"Retriever",
            END:END
            })
        
        workflow.add_conditional_edges("Retriever", self._route_after_retriever,
                                      {"Generator": "Generator",
                                       "WebSearch":"WebSearch"} )
        
        workflow.add_edge("WebSearch", "Generator")
        workflow.add_edge("Generator", END)

        return workflow
    def run_pipeline(self, question) -> str:
        thread_id = str(uuid.uuid4())
        initial_question = {
            "messages": [HumanMessage(content=question)]
        }

        result = asyncio.run(
            self.app.ainvoke(
                initial_question,
                config={"configurable": {"thread_id": thread_id}}
            )
        )

        print("🧾 FULL RESULT:", result)  # debug

        # ✅ ALWAYS RETURN FINAL ANSWER ONLY
        return result.get("answer", "No response generated")

if __name__ =="__main__":
    rag=AgenticRAG()
    question= "Can you Provide me feeback of realme Mobclsiles"
    rag.run_pipeline(question)

# python -m  prod_assistant.workflow.agentic_workflow_with_mcp_webresearch


    

    

    

    








































#     This ADD Main File
# @app.on_event("startup")
# async def startup():
#   await agent.initialize()