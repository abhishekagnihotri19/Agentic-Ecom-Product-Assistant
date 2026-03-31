from typing import Annotated, Sequence, TypedDict, Literal
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.messages import AIMessage

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from prod_assistant.prompt_library.prompts import PromptRegistry, PromptType
from prod_assistant.retriever.retrieval import Retriever
from prod_assistant.utils.model_loader import ModelLoader
from langgraph.checkpoint.memory import MemorySaver
import asyncio

class AgenticRAG:
        
        """Agentic RAG pipeline using LangGraph."""
       
        class AgentState(TypedDict, total= False):  
                # total= False, meaning following total variable are optional, not Mandatory
                messages: Annotated[Sequence[BaseMessage],add_messages]
                question:str  # original user input
                query:str  # search query (may be rewritten)
                context:str # formatted retrieved documents
                answer:str # final generated answer
                needs_retrieval: bool  # routing decision


        def __init__(self):
                self.retriever_obj= Retriever()
                self.model_loader= ModelLoader()
                self.llm= self.model_loader.load_llm()
                self.checkpointer=MemorySaver()
                self.workflow= self._build_workflow()
                self.app= self.workflow.compile(checkpointer=self.checkpointer)



        def format_docs(self, docs) -> str:
                """Helper Function for Formatting"""
                """Chunks Should be formatted well, before Inserting into LLM"""
                if not docs:
                        return "No relevant documents found."

                formatted_chunks = []

                for d in docs:
                        meta = getattr(d, "metadata", {}) or {}
                        content = getattr(d, "page_content", "").strip()

                        formatted_chunks.append(
                        "\n".join([
                                f"Title: {meta.get('title', 'N/A')}",
                                f"Price: {meta.get('price', 'N/A')}",
                                f"Rating: {meta.get('rating', 'N/A')}",
                                "Review:",
                                content
                        ])
                        )

                return "\n\n" + "-" * 40 + "\n\n".join(formatted_chunks)
        
        """Entry State"""
        def entry_state(self, state :AgentState):
                print("----Entry State----")
                question= state["messages"][-1].content
                return {"question": question}

        """AI Assitant Works Starts"""
        def _ai_assistant(self, state:AgentState):
                print ("----Assiatant Working starts------")
                question= state["question"] 
                keywords= ['price', 'review', 'product']
                needs_retrieval= any (k in question.lower() for k in keywords)
                if needs_retrieval:
                        return {
                                "query": question,
                                "needs_retrieval": True, }
                
                # Direct Answer if not Required retriever

                prompt=ChatPromptTemplate.from_template(" You are the heplful Assistant, \n\n Answer the Question : {question} directly \nAnswer:")
                chain= prompt|self.llm|StrOutputParser()
                response= chain.invoke ({"question": question})
                return  {"answer": response,
                         "needs_retrieval":False,
                        "messages": [AIMessage(content=response)]}
       
       
        """Router"""

        def _route_after_assistant(self, state:AgentState):
                if state["needs_retrieval"]:
                        return "Retriever"
                return END
        
        """Vector Retriver"""
        def vector_retriever(self, state: AgentState):
                print("--- RETRIEVER ---")
                query= state ["query"]
                docs= self.retriever_obj.call_retriever(query)
                context = self.format_docs(docs)
                return {"context": context}
        
        """Grader: To check Document"""

        def grader(self, state:AgentState) -> Literal ["generator", "rewriter"]:
                question= state["question"]
                context= state ["context"]
                prompt= ChatPromptTemplate.from_template("you are grader, please check question : {question} is relevant to Docs: {docs}, Answer me in yes or no")
                chain= prompt|self.llm|StrOutputParser()
                respond = chain.invoke({"question":question, "docs": context})
                if "yes" in respond.lower():
                        return "generator"
                return "rewriter"

        def generator(self, state:AgentState):
                question= state["question"]
                context= state["context"]
                prompt = ChatPromptTemplate.from_template(PromptRegistry[PromptType.PRODUCT_BOT].template)
                #prompt= ChatPromptTemplate.from_template("you are the AI Assitant Answer is directly question:{question}, context:{context}")
                response_gen_chain= prompt|self.llm| StrOutputParser()
                gen_ans= response_gen_chain.invoke({"question":question, "context": context})
                return {"answer": gen_ans,
                        "messages": [AIMessage(content=gen_ans)],}
        
        def rewriter(self, state:AgentState):
                question= state["question"]
                prompt= ChatPromptTemplate.from_template( "Rewrite the following query to improve retrieval:\n\n{question}")
                chain= prompt|self.llm| StrOutputParser()
                new_query= chain.invoke({"question":question})
                return {"query":new_query}
        
        #---------------------Build Workflow------------------------
        def _build_workflow(self):
                workflow=StateGraph(self.AgentState)
                workflow.add_node("Entry", self.entry_state)
                workflow.add_node("Assistant", self._ai_assistant)
                workflow.add_node("Retriever", self.vector_retriever)
                workflow.add_node("Generator", self.generator)
                workflow.add_node("Rewriter", self.rewriter)

                workflow.set_entry_point ("Entry")

                workflow.add_edge("Entry", "Assistant")
                
                workflow.add_conditional_edges(
                "Assistant",
                self._route_after_assistant,
                {
                        "Retriever": "Retriever",
                        END: END
                }
                )

                workflow.add_edge("Retriever", "Generator")
                workflow.add_edge("Generator", END)
                
                # workflow.add_conditional_edges("Retriever", self.grader,{
                #         "generator":"Generator",
                #         "rewriter":"Rewriter"
                # })
                # workflow.add_edge("Generator", END)
                # workflow.add_edge("Rewriter", "Retriever")

                return workflow
        def run(self, question:str, thread_id:str="default_thread")->str:
                initial_question= {
                        "messages": [HumanMessage(content=question)]
                }
                result= self.app.invoke(initial_question, config={"configurable":{"thread_id": thread_id}})
                return result["answer"]

if __name__=="__main__":
        rag= AgenticRAG()
        question= "what is the price of iphone 16?"
        answer=rag.run(question=question)
        print ("\n---Final Answer---\n", answer)







# python -m  prod_assistant.workflow.agentic_rag_workflow





        # def format_docs(docs)->str:
        #         if not docs:
        #                 raise ValueError ("Documents not found")
        #         formatted_chunks= []
        #         for d in docs:
        #                 meta= d.metadata or {}
        #                 formatted= ( f"Title: {meta.get('title', 'N/A')}\n"   
        #                         f"Price:{meta.get('price', 'N/A')}\n"
        #                         f"Rating:{meta.get('rating', 'N/A')}\n"
        #                          f"Review:\n{d.page_content.strip()}"       
        #                          )   
        #                 formatted_chunks.append(formatted)  
        #         return "\n\n-----\n\n".join(formatted_chunks) 



        
        # def _ai_assiatant(self, state: AgentState):
        #         print ("----Calling Assistant----")
        #         messages= state["messages"]
        #         last_message= messages[-1].content
        #         if any ("Title", "Price", "Rating") in last_message:
        #                 if any(word in last_message.lower() for word in ["price", "review", "product"]):
        #                         return {"messages":[ HumanMessage(content="Tool: retriever")]}
        #         else:
        #                 prompt= ChatPromptTemplate.from_template(" You are the heplful Assistant \n\n Answer the Question{question} directly \nAnswer")
        #                 chain= prompt| self.llm | StrOutputParser()
        #                 response= chain.invoke ({"question":last_message})
        #                 return {"messages": [HumanMessage(content=response)]}

        # def vector_retriever(self, state:AgentState):
        #         print ("-----Retriever Role Starts------")
        #         query= state["messages"][-1].content
        #         retriever= self.retriver_obj.load_retriever
        #         docs= retriever.invoke(query)
        #         context= self.format_docs(docs)
        #         return {"messages": [HumanMessage(content=context)] }
        
       
                
                        

        