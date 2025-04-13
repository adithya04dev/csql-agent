from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Literal, Set
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
    def __init__(self, initial_examples_dir=None):
        self.embeddings = OpenAIEmbeddings(model='text-embedding-3-large')
        self.tables_dir = "./agents/tables"

        self.stores = {}
        self.retrievers = {}
        self.available_categories = set()
        self.scan_available_categories()
        
    def scan_available_categories(self):
        """Scan directory to identify available categories without loading stores"""
        for table_name in os.listdir(self.tables_dir):
            table_dir = os.path.join(self.tables_dir, table_name)
            if os.path.isdir(table_dir):
                for filename in os.listdir(table_dir):
                    if filename.endswith(".txt"):
                        category = filename[:-4]  # Remove .txt extension
                        table_category = f"{table_name}_{category}"
                        self.available_categories.add(table_category)
                    elif filename.endswith('.json'):
                        category = filename.replace(".txt", "").replace('.json','')
                        table_category = f"{table_name}_{category}"
                        self.available_categories.add(table_category)

    def load_store(self, table_category: str):
        """Load a specific vector store on demand"""
        if table_category in self.stores:
            return self.stores[table_category]
            
        if table_category not in self.available_categories:
            print(f"Warning: Category '{table_category}' not found in available categories.")
            return None
            
        table_name, category = table_category.rsplit('_', 1)
        table_dir = os.path.join(self.tables_dir, table_name)
        store_path = os.path.join(table_dir, table_category)
        
        # Check for text or json file
        txt_file = os.path.join(table_dir, f"{category}.txt")
        json_file = os.path.join(table_dir, f"{category}.json")
        
        if os.path.exists(store_path):
            print(f"Loading store for category '{table_category}' from '{store_path}'")
            self.stores[table_category] = FAISS.load_local(
                store_path, self.embeddings, allow_dangerous_deserialization=True
            )
        else:
            print(f"Creating store for category '{table_category}'")
            os.makedirs(store_path, exist_ok=True)
            self.stores[table_category] = FAISS.from_texts(
                ["placeholder"], self.embeddings
            )
            
            # Add examples if file exists
            if os.path.exists(txt_file):
                self.add_examples_from_file(txt_file)
            elif os.path.exists(json_file):
                self.add_examples_from_file(json_file)
                
        self.retrievers[table_category] = self.stores[table_category].as_retriever(search_kwargs={"k": 5})
        return self.stores[table_category]

    def add_examples_from_file(self, file_path: str):
        """Adds examples from a .txt file to the corresponding vector store."""
        table_name = os.path.basename(os.path.dirname(file_path)) # Extract table name from the path
        category = os.path.basename(file_path).replace(".txt", "").replace(".json","")

        table_category = f"{table_name}_{category}" # Create table_category

        # Load store if not already loaded
        if table_category not in self.stores:
            self.load_store(table_category)
            
        if table_category not in self.stores:
            print(f"Warning: No store found for category '{table_category}'. Skipping.")
            return
            
        if file_path.endswith('.txt'):            
            with open(file_path, "r", encoding='utf-8') as f:
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
            print("adding file name", filename)
            if filename.endswith(".txt") or filename.endswith(".json"):
                file_path = os.path.join(dir_path, filename)
                self.add_examples_from_file(file_path)

    async def search_similar_queries(self, query: str, table_category: str, k: int = 5) -> str:
        """Search for similar queries in a specific category's vector store"""
        # Lazy load the store if not already loaded
        if table_category not in self.stores:
            self.load_store(table_category)
            
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
# vector_store_manager = VectorStoreManager()
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