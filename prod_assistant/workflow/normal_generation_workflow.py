from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from prod_assistant.prompt_library.prompts import PromptTemplate, PromptRegistry,PromptType
from retriever.retrieval import Retriever
from prod_assistant.utils.model_loader import ModelLoader

retreiver_obj= Retriever()
model_loader= ModelLoader()

def format_docs(docs)->str:
    if not docs:
        raise ValueError (" No Docs Found")
    formatted_chunks=[]
    for d in docs:
        meta= d.metadata or {}
        formatted = ( f"Title: {meta.get('product_title', 'N/A')}\n"
            f"Price:{meta.get('price', 'N/A')}\n"
            f"Rating:{meta.get('rating', 'N/A')}\n"
            f"Review: \n{d.page_content.strip()}"
            )
        formatted_chunks.append(formatted)
    return "\n\n----\n\n".join (formatted_chunks)

def build_chain(query):
    retriever= retreiver_obj.load_retriever()
    retrieved_docs= retriever.invoke(query)
    retrieved_context= format_docs(retrieved_docs)

    llm= model_loader.load_llm()

    prompt= ChatPromptTemplate.from_template(
        PromptRegistry[PromptType.PRODUCT_BOT].template     
    )
    chain= (
        {"context": retriever | format_docs, "question" : RunnablePassthrough()}
    
    | prompt 
    | llm
    | StrOutputParser()
    )
    return chain, retrieved_context

def invoke_chain(query: str, debug: bool= False):
        """Run the chain with a user query."""
        chain = build_chain(query=query)
        if debug:
        # For debugging: show docs retrieved before passing to LLM
            docs= retreiver_obj.load_retriever().inovoke(query)
            print("\n Retrieved Documents: ")
            print (format_docs(docs))
            print ("\n-----\n")
        response= chain.invoke(query)
        return response
        

if __name__ == "__main__":
     try:
         answer = invoke_chain("can you tell me the price of the iPhone 15?")
         print("\n Assistant Answer:\n", answer)
     except Exception as e:
        import traceback
        print("Exception occurred:", str(e))
        traceback.print_exc()
