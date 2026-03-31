import os
from prod_assistant.utils.config_loader import load_config
from prod_assistant.utils.model_loader import ModelLoader
from typing import List, Any
from dotenv import load_dotenv
#from langchain_core.retrievers import ContextualCompressionRetriever
#from langchain.retrievers import ContextualCompressionRetriever
#from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_core.vectorstores import VectorStoreRetriever
from typing import List, Tuple, Union
from langchain_core.documents import Document
import httpx

from langchain_astradb import AstraDBVectorStore
from prod_assistant.evaluation.eval_ragas import evaluate_context_precision, evaluate_response_relevancy




class Retriever:
    def __init__(self):
        self.config= load_config()
        self.model_loader= ModelLoader()
        load_dotenv()
        self.vstore= None
        self.retreival_instance= None
        self.load_env_variable()
    
    def load_env_variable(self):
        load_dotenv()
        required_variable= ["GOOGLE_API_KEY","GROQ_API_KEY", "ASTRA_DB_APPLICATION_TOKEN", "ASTRA_DB_KEYSPACE", "ASTRA_DB_API_ENDPOINT" ]

        missing_var= [var for var in required_variable if os.getenv(var) is None]

        if missing_var:
            raise EnvironmentError(f"Missing Enviromental Variable{missing_var}")

        self.google_api_key= os.getenv ("GOOGLE_API_KEY")
        self.groq_api_key= os.getenv ("GROQ_API_KEY")
        self.astra_db_token= os.getenv ("ASTRA_DB_APPLICATION_TOKEN")
        self.astra_db_keyspace= os.getenv ("ASTRA_DB_KEYSPACE")
        self.astra_db_api_endpoint= os.getenv ("ASTRA_DB_API_ENDPOINT")

    def load_retriever(self):

        if not self.vstore:
            collection_name= self.config["astra_db"]["collection_name"]
           # http_client = httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0))
            
            self.vstore=AstraDBVectorStore(
                embedding= self.model_loader.load_embedding(),
                collection_name= collection_name,
                api_endpoint= self.astra_db_api_endpoint,
                token= self.astra_db_token,
                namespace=self.astra_db_keyspace,
                #timeout=30,
                #http_client=http_client,


            )
        if not self.retreival_instance:
            top_k = self.config["retriever"]["top_k"] if "retriever" in self.config else 3

            #mmr_retriever= self.vs.as_retriever (
                #search_type= "mmr",
                #search_kwargs= {
                  #  "k":top_k,
                  #  "fetch_k": 20,
                  #  "lambda_mult": 0.7,
                  #  "score_threshold": 0.6
            #}
            #)
            self.retreival_instance = self.vstore.as_retriever(
               search_kwargs={"k":top_k}
           )
            print ("Retriever Loaded Succesfully")

        # if not self.compressor:
        #     self.compressor= EmbeddingsFilter(
        #         embeddings= self.model_loader.load_embedding(),
        #         similarity_threshold=0.7

        #     )
          
        #     print("Retriever with EmbeddingsFilter loaded successfully.")
        return self.retreival_instance
    
    def call_retriever(self, query:str):
        retriever= self.load_retriever()
        output = retriever.invoke(query)
        print(f"🔍 Retrieved {len(output)} documents")
        #compressed_docs = self.compressor.compress_documents(
        #docs=output,
        #query=query)

        return output


if __name__ =='__main__':
    user_query= "can you suggest me any i phone or samsung phone"
    retrievr_obj= Retriever()
    retrieved_docs= retrievr_obj.call_retriever(user_query)
    docs = retrievr_obj.call_retriever(user_query)
    print(type(docs))

    docs = retrievr_obj.call_retriever(user_query)

    for i, doc in enumerate(docs, start=1):
        print(f"\n--- Document {i} ---")
        print("Type:", type(doc))
        print("Content preview:", str(doc)[:300])



   

    # def _format_docs_llm(docs) -> str:  
    #     if not docs:
    #         return "No relevant documents found."

    #     formatted_chunks = []

    #     for d in docs:
    #         # 🔹 Handle (Document, score)
    #         if isinstance(d, tuple):
    #             d = d[0]

    #         meta = d.metadata or {}
  
    #     formatted=(
    #             f"Title: {meta.get('product_title', 'N/A')}\n"
    #             f"Price:{meta.get('product_price', 'N/A')}\n"
    #             f"Rating: {meta.get ('product_rating', 'N/A')}\n"
    #             f"Review: \n{d.page_content.strip()}"
    #         )
    #     formatted_chunks.append(formatted)

    #     return "\n\n--\n\n".join (formatted_chunks)

    # retrieved_contexts_llm = _format_docs_llm(retrieved_docs)
    # response="iphone 16 plus, iphone 16, iphone 15 are best phones under 1,00,000 INR."

    # def format_docs_for_ragas(docs) -> list[str]:
    #     contexts = []

    #     for d in docs:
    #         if isinstance(d, tuple):
    #             d = d[0]
    #         if not d.page_content or not isinstance(d.page_content, str):
    #             continue  # 🔥 critical for Groq
    #         meta = d.metadata or {}

    #         text = (
    #             f"Title: {meta.get('product_title', 'N/A')}\n"
    #             f"Price: {meta.get('product_price', 'N/A')}\n"
    #             f"Rating: {meta.get('product_rating', 'N/A')}\n"
    #             f"Review:\n{d.page_content.strip()}"
    #         )

    #         contexts.append(text)

    #     return contexts
    # context_raga= format_docs_for_ragas(retrieved_docs)

    
    # context_score = evaluate_context_precision(user_query, response, context_raga)
    # relevancy_score = evaluate_response_relevancy(user_query, response,context_raga)
    
    # print("\n--- Evaluation Metrics ---")
    # print("Context Precision Score:", context_score)
    # print("Response Relevancy Score:", relevancy_score)
    

   
