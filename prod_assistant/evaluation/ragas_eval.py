import asyncio
from prod_assistant.utils.model_loader import ModelLoader
from ragas import SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
#from ragas.metrics import (LLMContextPrecessionWithoutReference, ResponseRelevancy)
from ragas.metrics import ContextPrecision, ResponseRelevancy

import grpc.experimental.aio as grpc_aio
grpc_aio.init_grpc_aio()
model_loader= ModelLoader()

def evaluate_context_precission(query, response, contexts):
    try:
        sample= SingleTurnSample(
            query= query,
            retrieved_contexts= contexts,
            response= response
        )

        async def main():
            llm= model_loader.load_llm()
            evaluator_llm= LangchainLLMWrapper(llm)
            context_precession= ContextPrecision(llm= evaluator_llm)
            result= await context_precession.single_turn_ascore(sample)
            return result
        return asyncio.run(main())
    except Exception as e:
        return e

def evaluate_response_relevancy(query, response, contexts):
    try:
        sample= SingleTurnSample(
            query= query,
            retrieved_contexts=contexts,
            response=response
        )

        async def main():
            llm= model_loader.load_llm()
            evaluator_llm= LangchainLLMWrapper(llm)
            embedding_model= model_loader.load_embedding()
            evaluator_embed= LangchainEmbeddingsWrapper(embedding_model)
            relevancy_score= ResponseRelevancy(llm=evaluator_llm, embeddings=evaluator_embed)
            result= await relevancy_score.single_turn_ascore(sample)
            return result
        return asyncio.run(main())


    except Exception as e:
        return e


