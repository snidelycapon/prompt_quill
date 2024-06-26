import globals
import gc
import os


from llama_index.core.prompts import PromptTemplate
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.llms.llama_cpp.llama_utils import messages_to_prompt, completion_to_prompt
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import qdrant_client




url = "http://localhost:6333"

if os.getenv("QDRANT_URL") is not None:
    url = os.environ["QDRANT_URL"]

class adapter:

    def __init__(self):
        self.index='prompts_large_meta'
        self.g = globals.get_globals()
        self.document_store = self.set_document_store()
        self.llm = self.set_llm()
        self.set_pipeline()
        self.last_context = []

    def get_instruct(self):
        return self.g.settings_data['Instruct Model']
    def get_document_store(self):
        return self.document_store

    def set_document_store(self):
        return qdrant_client.QdrantClient(
            # you can use :memory: mode for fast and light-weight experiments,
            # it does not require to have Qdrant deployed anywhere
            # but requires qdrant-client >= 1.1.1
            #location=":memory:"
            # otherwise set Qdrant instance address with:
            url=url
            # set API KEY for Qdrant Cloud
            # api_key="<qdrant-api-key>",
        )

    def get_llm(self):
        return self.llm
    def set_llm(self):

        return LlamaCPP(

            model_url=self.g.settings_data['model_list'][self.g.settings_data['LLM Model']]['path'],

            # optionally, you can set the path to a pre-downloaded model instead of model_url
            model_path=None,

            temperature=self.g.settings_data["Temperature"],
            max_new_tokens=self.g.settings_data["max output Tokens"],

            # llama2 has a context window of 4096 tokens, but we set it lower to allow for some wiggle room
            context_window=self.g.settings_data["Context Length"],  # note, this sets n_ctx in the model_kwargs below, so you don't need to pass it there.

            # kwargs to pass to __call__()
            generate_kwargs={},

            # kwargs to pass to __init__()
            # set to at least 1 to use GPU, check with your model the number need to fully run on GPU might be way higher than 1
            model_kwargs={"n_gpu_layers": self.g.settings_data["GPU Layers"]}, # I need to play with this and see if it actually helps

            # transform inputs into Llama2 format
            messages_to_prompt=messages_to_prompt,
            completion_to_prompt=completion_to_prompt,
            verbose=True,
        )

    def get_retriever(self, similarity_top_k):
        return self.vector_index.as_retriever(similarity_top_k=similarity_top_k)

    def set_pipeline(self):

        if hasattr(self,'query_engine'):
            del self.vector_store
            del self.vector_index
            del self.query_engine


        self.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L12-v2")
        self.vector_store = QdrantVectorStore(client=self.document_store, collection_name=self.index)
        self.vector_index = VectorStoreIndex.from_vector_store( vector_store=self.vector_store, embed_model=self.embed_model)

        self.retriever = self.get_retriever(similarity_top_k=self.g.settings_data['top_k'])

        self.query_engine = self.vector_index.as_query_engine(similarity_top_k=self.g.settings_data['top_k'],llm=self.llm)

        self.qa_prompt_tmpl = PromptTemplate(self.g.settings_data['prompt_templates']['prompt_template_b'])

        self.query_engine.update_prompts(
            {"response_synthesizer:text_qa_template": self.qa_prompt_tmpl}
        )

    def retrieve_context(self, prompt):
        return self.retriever.retrieve(prompt)


    def get_context_text(self, query):
        nodes = self.retrieve_context(query)
        return [s.node.get_text() for s in nodes]


    def prepare_meta_data(self, response):
        self.g.negative_prompt_list = []
        self.g.models_list = []
        negative_prompts = []
        for key in response.metadata.keys():
            if 'negative_prompt' in response.metadata[key]:
                negative_prompts = negative_prompts + response.metadata[key]['negative_prompt'].split(',')
                self.g.models_list.append(f'{response.metadata[key]["model_name"]}')

            if len(negative_prompts) > 0:
                self.g.negative_prompt_list = set(negative_prompts)



    def retrieve_query(self, query):
        response =  self.query_engine.query(query)
        self.g.last_context = [s.node.get_text() for s in response.source_nodes]
        return response.response.lstrip(" ")


    def change_model(self,model,temperature,n_ctx,n_gpu_layers,max_tokens,top_k, instruct):

        self.g.settings_data["Context Length"] = n_ctx
        self.g.settings_data["GPU Layers"] = n_gpu_layers
        self.g.settings_data["max output Tokens"] = max_tokens
        self.g.settings_data["Temperature"] = float(temperature)
        self.g.settings_data["top_k"] = top_k
        self.g.settings_data['Instruct Model'] = instruct
        self.g.settings_data['LLM Model'] = model["name"]

        self.llm._model = None
        del self.llm

        self.llm = self.set_llm()

        # delete the model from Ram
        gc.collect()

        self.set_pipeline()
        return f'Model set to {model["name"]}'

    def set_prompt(self,prompt_text):

        self.g.settings_data['prompt_templates']['prompt_template_b'] = prompt_text

        self.log('magic_prompt_logfile.txt',f"Magic Prompt: \n{prompt_text} \n")

        self.llm._model = None
        del self.llm

        # delete the model from Ram
        gc.collect()

        self.llm = self.set_llm()

        self.set_pipeline()
        return f'Magic Prompt set to:\n {prompt_text}'