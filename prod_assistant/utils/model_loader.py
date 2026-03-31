from prod_assistant.utils.config_loader import load_config
import os
from  dotenv import load_dotenv
import json
from typing import Optional, Any
import sys
from prod_assistant.exception.custom_exception import ProductAssistantException
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from prod_assistant.logger import GlobalLogger as log
import asyncio
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError


load_dotenv()


class ApiKeyManager:
    def __init__(self):
       self.api_keys = {"GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
                        "OPENAI_API_KEY": os.getenv ("OPENAI_API_KEY"),
                        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
                        "ASTRA_DB_API_KEY" : os.getenv("ASTRA_DB_API_KEY"),
                        "ASTRA_DB_KEYSPACE" : os.getenv("ASTRA_DB_KEYSPACE"),
                        "ASTRA_DB_APPLICATION_TOKEN" : os.getenv ("ASTRA_DB_APPLICATION_TOKEN"),}
       for key, val in self.api_keys.items():
           if val:
               log.info(f"{key}loaded from enviroments")
           else:
               log.warning (f"{key} is missing from enviroments")

    def get_key(self,my_key:str):
        return self.api_keys.get(my_key)




class ModelLoader:
    def __init__(self):
        self.api_key_manager= ApiKeyManager()
        self.config = load_config()
        log.info ("YAML Config loaded", Config_keys= list(self.config.keys()))

    def load_embedding (self):
        """Load and return Embedding Model from Google Generative AI"""
        try:
            model_name= self.config["embedding_model"]["model_name"]
            log.info ("Loading Embedding Model", model= model_name)

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())
            return GoogleGenerativeAIEmbeddings (model= model_name,
                                                 google_api_key= self.api_key_manager.get_key("GOOGLE_API_KEY"))

        except Exception as e:
            log.error ("Error Loading Embedding Model", error=str(e))
            raise ProductAssistantException ("Failed to Load Embedding Model", sys)
        
    def load_llm(self):
        try:
            llm_block= self.config["llm"]
            provider_key= os.getenv("LLM_PROVIDER", "groq")

            if provider_key not in llm_block:
                log.error ("LLM provider not found in config", provider= provider_key)
                raise ValueError(f"LLM provider '{provider_key}' not found in config")

            llm_config = llm_block[provider_key]
            provider = llm_config.get("provider")
            if not provider:
                raise ValueError (f"provider not defined in config")
            model_name= llm_config.get("model_name")

            temperature = llm_config.get("temperature", 0)
            max_token = llm_config.get("max_tokens", 2048)

            PROVIDER_REGISTRY = {
                "google": lambda: ChatGoogleGenerativeAI(
                    model = model_name,
                    temperature = temperature,
                    max_tokens = max_token,
                    google_api_key= self.api_key_manager.get_key("GOOGLE_API_KEY")

                ),
                "groq" : lambda : ChatGroq (
                    model = model_name,
                    temperature = 0,
                    #max_completion_tokens = max_token,
                    max_retries=2,
                    groq_api_key = self.api_key_manager.get_key("GROQ_API_KEY")
                ),
                "openai" : lambda : ChatOpenAI (
                    model = model_name,
                    temperature = temperature,
                    max_tokens = max_token,
                    openai_api_key = self.api_key_manager.get_key("OPENAI_API_KEY")
                ),
            }

            if provider not in PROVIDER_REGISTRY:
                log.info ("LLM Not found", provider = provider)
                raise ValueError (f"Unsupported LLM Provider: {provider}")
            
            try:
                return PROVIDER_REGISTRY [provider]()
            except ChatGoogleGenerativeAIError:
                log.warning("Google Quota Exhausted, Switching to Groq")
                return PROVIDER_REGISTRY ["groq"]()


        except Exception as e:
            log.error("LLM Provider Unavailable", error=str(e))
            raise  


def safe_text(parent, by, selector, default="N/A"):
    try:
        return parent.find_element(by, selector).text.strip()
    except Exception:
        return default




if __name__ == "__main__":
       loader = ModelLoader()
       embedding= loader.load_embedding()
       print (f"Embedding model Loaded:{embedding}")
       result= embedding.embed_query("How are you Darling")
       print (f"Embedding concluded {result}")

       llm = loader.load_llm()
       print (f"LLM Model loaded succesfully: {llm}")
       result_llm= llm.invoke ("Can you come with me for a date?")
       print (f"Answer by LLM: {result_llm}")





# python -m prod_assistant.utils.model_loader

"""Below codes are in traditional way, But Not feasible for Production or Enterprise level"""

    # def load_llm(self):
    #     """Loading Large Language Model"""
    #     try:
    #         model_llm= self["google"]["llm_name"]
    #         log.info ("LLM model are Loading from YAML", model="llm_name")

    #        # llm_block= self.config["llm"][""]
    #         llm_block = self.config["llm"]
    #         provider_key = os.getenv["llm_provider", "OPEN_AI"]
    #         llm_config =  llm_block[provider_key]


    #         provider = llm_config.get("provider")
    #         model_name= llm_config.get("model_name")
    #         temprature= llm_config.get("temperature")
    #         max_token= llm_config.get("max_token")

    #         if provider == "google":
    #             return ChatGoogleGenerativeAI (model = model_name,
    #                                           temprature = temprature,
    #                                            max_tokens = max_token,
    #                                             google_api_key = self.api_key_manager.get_key("GOOGLE_API_KEY") )
    #         elif provider == "groq":
    #             return ChatGroq (model = model_name,
    #                              temperature = temprature,
    #                              max_tokens = max_token,
    #                              open_ai_api_key = self.api_key_manager.get_key("OPENAI_API_KEY"))
    #         elif provider == "open_ai":
    #             return ChatOpenAI (model = model_name,
    #                                temperature = temprature,
    #                                max_completion_tokens = max_token,
    #                                openai_api_key = self.api_key_manager.get_key("OPENAI_API_KEY"))


    #     except:
    #         pass

        