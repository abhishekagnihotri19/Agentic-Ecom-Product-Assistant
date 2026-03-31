import asyncio
from prod_assistant.utils.model_loader import ModelLoader
from ragas import SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import ContextPrecision, ResponseRelevancy

import grpc.experimental.aio as grpc_aio
grpc_aio.init_grpc_aio()

model_loader = ModelLoader()


def _sanitize_contexts(contexts: list[str]) -> list[str]:
    """Ensure RAGAS-safe contexts"""
    return [
        c for c in contexts
        if c and isinstance(c, str)
    ]


def evaluate_context_precision(query: str, response: str, contexts: list[str]) -> float:
    contexts = _sanitize_contexts(contexts)

    if not contexts:
        raise ValueError("No valid contexts provided for ContextPrecision")

    sample= SingleTurnSample(
        user_input=query,
        response=response,
        retrieved_contexts=contexts,
        reference=""
        )


    async def _run():
        llm = model_loader.load_llm()
        evaluator_llm = LangchainLLMWrapper(llm)

        metric = ContextPrecision(llm=evaluator_llm)
        return await metric.single_turn_ascore(sample)

    return asyncio.run(_run())


def evaluate_response_relevancy(query: str, response: str, contexts: list[str]) -> float:
    contexts = _sanitize_contexts(contexts)

    if not contexts:
        raise ValueError("No valid contexts provided for ResponseRelevancy")

    sample = SingleTurnSample(
        query=query,
        response=response,
        retrieved_contexts=contexts
    )

    async def _run():
        llm = model_loader.load_llm()
        evaluator_llm = LangchainLLMWrapper(llm)

        embedding_model = model_loader.load_embedding()
        evaluator_embed = LangchainEmbeddingsWrapper(embedding_model)

        metric = ResponseRelevancy(
            llm=evaluator_llm,
            embeddings=evaluator_embed
        )

        return await metric.single_turn_ascore(sample)

    return asyncio.run(_run())
