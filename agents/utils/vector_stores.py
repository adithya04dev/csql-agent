from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Literal
import json
import os
from dotenv import load_dotenv
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import FlashrankRerank
from langchain_openai import ChatOpenAI
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
import asyncio
load_dotenv()

class VectorStoreManager:
    def __init__(self,initial_examples_dir=None):
        self.embeddings = OpenAIEmbeddings(model='text-embedding-3-large')
        self.tables_dir = "./agents/tables"

        self.stores = {}
        self.retrievers = {}
        self.initialize_stores()

    def initialize_stores(self):
        """Dynamically creates vector stores based on .txt files in tables/ directory."""
        for table_name in os.listdir(self.tables_dir):
            table_dir = os.path.join(self.tables_dir, table_name)
            # print("in table dir",table_dir)
            if os.path.isdir(table_dir):
                for filename in os.listdir(table_dir):
                    # print("in file name",filename)
                    if filename.endswith(".txt"):
                        category = filename[:-4]  # Remove .txt extension
                        table_category = f"{table_name}_{category}" # Create the unique table_category identifier
                        store_path = os.path.join(table_dir, table_category)

                        if os.path.exists(store_path):
                            # print(f"Loading store for category '{table_category}' from '{store_path}'")
                            self.stores[table_category] = FAISS.load_local(
                                store_path, self.embeddings, allow_dangerous_deserialization=True
                            )
                        else:
                            print(f"Creating store for category '{table_category}'")
                            os.makedirs(store_path, exist_ok=True)
                            self.stores[table_category] = FAISS.from_texts(
                                ["placeholder"], self.embeddings
                            )
                        self.retrievers[table_category] = self.stores[table_category].as_retriever(search_kwargs={"k": 5})
                    elif filename.endswith('.json'):
                        category = filename.replace(".txt","").replace('.json','')  # Remove .txt extension
                        table_category = f"{table_name}_{category}" # Create the unique table_category identifier
                        store_path = os.path.join(table_dir, table_category)

                        if os.path.exists(store_path):
                            # print(f"Loading store for category '{table_category}' from '{store_path}'")
                            self.stores[table_category] = FAISS.load_local(
                                store_path, self.embeddings, allow_dangerous_deserialization=True
                            )
                        else:
                            print(f"Creating store for category '{table_category}'")
                            os.makedirs(store_path, exist_ok=True)
                            self.stores[table_category] = FAISS.from_texts(
                                ["placeholder"], self.embeddings
                            )
                            self.add_examples_from_file(os.path.join(table_dir, filename))


                        self.retrievers[table_category] = self.stores[table_category].as_retriever(search_kwargs={"k": 5})
    def add_examples_from_file(self, file_path: str):
        """Adds examples from a .txt file to the corresponding vector store."""
        table_name = os.path.basename(os.path.dirname(file_path)) # Extract table name from the path
        category = os.path.basename(file_path).replace(".txt", "").replace(".json","")

        table_category = f"{table_name}_{category}" # Create table_category

        if table_category not in self.stores:
            print(f"Warning: No store found for category '{table_category}'. Skipping.")
            return
        if file_path.endswith('.txt'):            
            with open(file_path, "r",encoding='utf-8') as f:
                content = f.read()

            examples = content.strip().split("\n")
        
        elif file_path.endswith('.json'):
            with open(file_path, "r", encoding='utf-8') as f:
                content = json.load(f)

            examples = [json.dumps(example) for example in content]  # Convert each example to a JSON string

        if self.stores[table_category] is None:
            self.stores[table_category] = FAISS.from_texts(
                examples,
                self.embeddings
            )
        else:
            self.stores[table_category].add_texts(examples)

        self.retrievers[table_category] = self.stores[table_category].as_retriever(search_kwargs={"k": 5})

        # Save the updated store
        store_path = os.path.join(self.tables_dir, table_name, table_category)
        self.stores[table_category].save_local(store_path)

    def add_examples_from_directory(self, dir_path: str):
        """Adds examples from all .txt files in a directory."""
        for filename in os.listdir(dir_path):
            print("adding file name",filename)
            if filename.endswith(".txt"):
                file_path = os.path.join(dir_path, filename)
                self.add_examples_from_file(file_path)

    async def search_similar_queries(self, query: str, table_category: str, k: int = 5) -> str:
        """Search for similar queries in a specific category's vector store"""
        retriever = self.retrievers.get(table_category)

        if retriever is None:
            print(f"Warning: No retriever found for category '{table_category}'.")
            return []

        results = await retriever.ainvoke(query)
        
        # Collect results in a list first
        result_texts = [doc.page_content for doc in results[:k]]
        
        # Join them together in one operation
        return f"similar values of {query} in table are:\n{'\n'.join(result_texts)}"

# Example Usage
vector_store_manager = VectorStoreManager()
# vector_store_manager.add_examples_from_directory("agents/tables/ipl_hawkeye") # Still adds from the directory
# vector_store_manager.add_examples_from_directory("agents/tables/hdata_2403") # Still adds from the directory

# import asyncio

# async def main():
#     # print(await vector_store_manager.search_similar_queries("v kohli", "odata_2403_player")) 
#     # print(await vector_store_manager.search_similar_queries("kewna maphaka", "odata_2403_player")) 
#     # print(await vector_store_manager.search_similar_queries("back length", "odata_2403_length")) 
#     # print(await vector_store_manager.search_similar_queries("kohli", "ipl_hawkeye_player"))
#     # print(await vector_store_manager.search_similar_queries("back length", "ipl_hawkeye_ball_length")) 

#     print(await vector_store_manager.search_similar_queries("ipl 2024", "hdata_2403_competition"))



# asyncio.run(main())