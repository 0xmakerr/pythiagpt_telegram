import os
import openai
import tiktoken
from dotenv import load_dotenv
from threading import Lock
from llama_index import (ServiceContext,
                         StorageContext,
                         load_index_from_storage,
                         set_global_service_context)
from llama_index.callbacks import CallbackManager, TokenCountingHandler
from llama_index.llms import OpenAI
from base_prompt import CHAT_REFINE_PROMPT, CHAT_QA_PROMPT
from llama_index.evaluation import ResponseEvaluator
from llama_index.indices.postprocessor import SentenceTransformerRerank

load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]
thread_lock = Lock()

# setup token counter
token_counter = TokenCountingHandler(tokenizer=tiktoken.encoding_for_model("gpt-3.5-turbo").encode)
callback_manager = CallbackManager([token_counter])
# define LLM
llm = OpenAI(temperature=0, model="gpt-3.5-turbo", streaming=False, max_tokens=1000)
service_context = ServiceContext.from_defaults(llm=llm, callback_manager=callback_manager, embed_model="local")
set_global_service_context(service_context)


def pyth_gpt(message):
    global service_context

    with thread_lock:
        # rebuild storage context
        storage_context = StorageContext.from_defaults(persist_dir="./storage")
        # load index
        index = load_index_from_storage(storage_context, service_context=service_context)

        rerank = SentenceTransformerRerank(model="cross-encoder/ms-marco-MiniLM-L-2-v2", top_n=3)
        # query the index
        query_engine = index.as_query_engine(text_qa_template=CHAT_QA_PROMPT,
                                             refine_template=CHAT_REFINE_PROMPT,
                                             similarity_top_k=10,
                                             streaming=False,
                                             service_context=service_context,
                                             node_postprocessors=[rerank])
        # enter your prompt
        response = query_engine.query(message)
        # define evaluator
        evaluator = ResponseEvaluator(service_context=service_context)
        # evaluate if the response matches any source context (returns "YES"/"NO")
        eval_result = evaluator.evaluate(response)
        print("Response matches any source context: " + str(eval_result))
        # token counter
        print('Embedding Tokens: ', token_counter.total_embedding_token_count, '\n',
              'LLM Prompt Tokens: ', token_counter.prompt_llm_token_count, '\n',
              'LLM Completion Tokens: ', token_counter.completion_llm_token_count, '\n',
              'Total LLM Token Count: ', token_counter.total_llm_token_count, '\n')
        token_counter.reset_counts()

        return str(response)
