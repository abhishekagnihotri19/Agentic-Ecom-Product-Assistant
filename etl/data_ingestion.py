import os
import pandas as pd
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_astradb import AstraDBVectorStore
from prod_assistant.utils.model_loader import ModelLoader
from typing import List
from prod_assistant.utils.config_loader import load_config


class DataIngestion:
    def __init__(self):
        self.config= load_config()
        self.model_loader= ModelLoader()
        self._load_env()
        self.csv= self._get_csv_path()
        self.data_frame_csv= self._load_csv()

    def _load_env(self):
        load_dotenv()
        required_var= ["GOOGLE_API_KEY", "GROQ_API_KEY", "ASTRA_DB_API_ENDPOINT", "ASTRA_DB_APPLICATION_TOKEN", "ASTRA_DB_KEYSPACE"]
        missing_var= [ var for var in required_var if os.getenv(var) is None]
        if missing_var:
            raise EnvironmentError (f"Missing Enviroment variable : {missing_var}")
        self.google_api_key= os.getenv ("GOOGLE_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.db_api_endpoint= os.getenv("ASTRA_DB_API_ENDPOINT")
        self.db_application_token= os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        self.db_keyspace= os.getenv("ASTRA_DB_KEYSPACE")

    def _get_csv_path(self):
        current_dir= os.getcwd()
        csv_path= os.path.join (current_dir, 'data', 'product_reviews.csv')
        if not os.path.exists(csv_path):
            raise FileNotFoundError (f"CSV file not found at {csv_path}")
        return csv_path
    
    def _load_csv(self):
        """Loading DataFrame, all data of CSV in df"""
        df = pd.read_csv(self.csv)
        expected_columns= {"product_id", "title", "price", "rating", "total_review", "top_reviews"}
        if not expected_columns.issubset(set(df.columns)):
            raise ValueError (f"CSV must contain all {expected_columns}")
        return df
    
    def transform_data(self):
        """"Transforming data in the list of Langchain Documents object"""
        product_list = []

        for _, row in self.data_frame_csv.iterrows():
            product_specification = {
                "product_id": row["product_id"],
                "product_title": row["title"],
                "product_price": row["price"],
                "product_rating": row["rating"],
                "product_review": row["total_review"],
                "top_review": row ["top_reviews"]

            }

            product_list.append(product_specification)
        documents=[]

        for item in product_list:
            meta_data= {
                "product_id": item["product_id"],
                "product_title": item["product_title"],
                "product_price": item["product_price"],
                "product_rating": item["product_rating"],
                "product_review":item["product_review"]
            }

            doc= Document(page_content = str(item["top_review"]), metadata=meta_data)
            documents.append(doc)

        print(f"Transformed{len(documents)} Documents")
        return documents
    
    def store_in_vector(self, documents:List[Document]):
        """Embedding in Vector Store"""
        collection_name= self.config["astra_db"]["collection_name"]
        vstore= AstraDBVectorStore(
            embedding= self.model_loader.load_embedding(),
            collection_name= collection_name,
            token=self.db_application_token,
            api_endpoint= self.db_api_endpoint,
            namespace=  self.db_keyspace
            

        )

        inserted_ids=vstore.add_documents(documents)
        print (f"Succesfully Inserted {len(inserted_ids)} documents into AstraDb")
        return vstore, inserted_ids
    def run_pipeline(self):
        """Run the full data pipeline"""
        documents= self.transform_data()
        vstore,_= self.store_in_vector(documents)

         #Optionally do a quick search
        query = "Can you tell me the low budget iphone?"
        results = vstore.similarity_search(query)

        print(f"\nSample search results for query: '{query}'")
        for res in results:
            print(f"Content: {res.page_content}\nMetadata: {res.metadata}\n")
    

if __name__ == "__main__":
    ingestion= DataIngestion()
    ingestion.run_pipeline()





