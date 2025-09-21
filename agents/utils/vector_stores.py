import time
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Literal, Set, Optional
import json
import os
from dotenv import load_dotenv
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import FlashrankRerank
from langchain_openai import ChatOpenAI
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
import asyncio
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams, UpdateCollection, HnswConfigDiff, OptimizersConfigDiff
from qdrant_client.http.exceptions import UnexpectedResponse
from enum import Enum
import gc  # For cleanup operations
load_dotenv()

class IndexingStrategy(Enum):
    """Indexing strategy for Qdrant vector store."""
    FAST = "fast"  # Fastest upload, high RAM usage
    MEMORY_EFFICIENT = "memory_efficient"  # Low memory usage, recommended
    DEFAULT = "default"  # Default behavior with immediate indexing

class VectorStoreManager:
    def __init__(self, initial_examples_dir=None):
        self.embeddings = OpenAIEmbeddings(model='text-embedding-3-large')
        self.tables_dir = "./agents/tables"
        self.storage_type = "cloud"  # Default to cloud if not specified
        self.embedding_size = 3072  # OpenAI text-embedding-3-large dimension
        
        # Remove caching - we'll query on-demand
        self.available_categories = set()
        
        # Initialize Qdrant client (lightweight singleton)
        if self.storage_type == "cloud":
            try:
                self.qdrant_url = os.getenv("QDRANT_URL")
                self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
                
                if not self.qdrant_url or not self.qdrant_api_key:
                    print("Warning: QDRANT_URL or QDRANT_API_KEY not set. Falling back to local storage.")
                    self.storage_type = "local"
                    self._init_local_storage()
                else:
                    self.qdrant_client = QdrantClient(
                        url=self.qdrant_url,
                        api_key=self.qdrant_api_key,
                        timeout=60,
                        prefer_grpc=True
                    )
                    print(f"✅ Connected to Qdrant cloud at {self.qdrant_url}")
            except Exception as e:
                print(f"Error connecting to Qdrant cloud: {str(e)}. Falling back to local storage.")
                self.storage_type = "local"
                self._init_local_storage()
        else:
            self._init_local_storage()

        self.scan_available_categories()
        
    def _init_local_storage(self):
        """Initialize local storage fallback"""
        self.local_stores = {}  # Keep minimal local cache for FAISS only
        
    def get_memory_usage(self):
        """Get current memory usage information."""
        if self.storage_type == "cloud":
            return {
                'storage_type': 'cloud',
                'cached_stores': 0,
                'estimated_size_mb': 5,  # Just client overhead
                'message': 'Using on-demand Qdrant queries - minimal memory usage'
            }
        else:
            import sys
            total_size = sum(sys.getsizeof(store) for store in self.local_stores.values())
            return {
                'storage_type': 'local',
                'cached_stores': len(self.local_stores),
                'estimated_size_mb': total_size / (1024 * 1024),
                'cached_store_names': list(self.local_stores.keys())
            }
        
    def clear_cache(self):
        """Clear local cache if using local storage"""
        if hasattr(self, 'local_stores'):
            print("Clearing local FAISS cache")
            self.local_stores.clear()
            gc.collect()

    def scan_available_categories(self):
        """Scan directory to identify available categories"""
        for table_name in os.listdir(self.tables_dir):
            table_dir = os.path.join(self.tables_dir, table_name)
            if os.path.isdir(table_dir):
                for filename in os.listdir(table_dir):
                    if filename.endswith((".txt", ".json")):
                        category = filename.replace(".txt", "").replace(".json", "")
                        table_category = f"{table_name}_{category}"
                        self.available_categories.add(table_category)

    def create_vector_store(
        self, 
        collection_name: str, 
        texts: Optional[List[str]] = None, 
        override: bool = False,
        indexing_strategy: IndexingStrategy = IndexingStrategy.DEFAULT,
        on_disk: bool = False,
        shard_number: Optional[int] = None,
        batch_size: int = 100
    ) -> QdrantVectorStore:
        """Create a new vector store collection in Qdrant (for data upload only)"""
        if self.storage_type != "cloud":
            print("create_vector_store only works with cloud storage")
            return None
            
        try:
            # If override is True, delete existing collection
            if override:
                try:
                    print(f"Deleting collection '{collection_name}' (override=True)")
                    self.qdrant_client.delete_collection(collection_name)
                    time.sleep(1)
                except Exception as e:
                    print(f"Note: Collection deletion: {str(e)}")
            
            # Configure indexing strategy
            hnsw_config = None
            optimizer_config = None
            
            if indexing_strategy == IndexingStrategy.FAST:
                optimizer_config = OptimizersConfigDiff(indexing_threshold=0)
            elif indexing_strategy == IndexingStrategy.MEMORY_EFFICIENT:
                hnsw_config = HnswConfigDiff(m=0)
            
            # Check if collection exists
            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
                if override:
                    self.qdrant_client.delete_collection(collection_name)
                    raise Exception("Forcing recreation after failed deletion")
                print(f"Collection '{collection_name}' already exists")
                if collection_info.config.params.vectors.size != self.embedding_size:
                    print(f"Recreating collection '{collection_name}' with correct vector size")
                    self.qdrant_client.delete_collection(collection_name)
                    raise Exception("Collection needs recreation")
                    
            except Exception as e:
                print(f"Creating new collection '{collection_name}'")
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_size,
                        distance=Distance.COSINE,
                        on_disk=on_disk
                    ),
                    hnsw_config=hnsw_config,
                    optimizers_config=optimizer_config,
                    shard_number=shard_number,
                )
            
            # Create vector store for upload
            vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=collection_name,
                embedding=self.embeddings
            )
            
            # Add initial texts in batches if provided
            if texts:
                unique_texts = list(set(texts))
                if len(unique_texts) < len(texts):
                    print(f"Removed {len(texts) - len(unique_texts)} duplicate texts")
                
                total_texts = len(unique_texts)
                for i in range(0, total_texts, batch_size):
                    batch = unique_texts[i:i + batch_size]
                    vector_store.add_texts(batch)
                    print(f"Added batch {i//batch_size + 1}/{(total_texts + batch_size - 1)//batch_size} "
                          f"({len(batch)} texts) to collection '{collection_name}'")

            if indexing_strategy == IndexingStrategy.FAST:
                print("Note: Indexing is disabled for fast upload. Enable it later using enable_indexing()")
            elif indexing_strategy == IndexingStrategy.MEMORY_EFFICIENT:
                print("Note: HNSW graph construction is deferred. Enable it later using enable_indexing()")
                
            return vector_store
            
        except Exception as e:
            print(f"Error with vector store: {str(e)}")
            return None

    def enable_indexing(self, collection_name: str, indexing_threshold: int = 20000, m: int = 16):
        """Enable indexing for a collection after bulk upload"""
        if self.storage_type != "cloud":
            return
            
        try:
            self.qdrant_client.update_collection(
                collection_name=collection_name,
                optimizer_config=OptimizersConfigDiff(
                    indexing_threshold=indexing_threshold
                ),
                hnsw_config=HnswConfigDiff(
                    m=m
                )
            )
            print(f"Enabled indexing for collection '{collection_name}'")
        except Exception as e:
            print(f"Error enabling indexing: {str(e)}")

    def add_examples_from_file(self, file_path: str, override: bool = False, indexing_strategy: IndexingStrategy = IndexingStrategy.DEFAULT, batch_size: int = 100):
        """Adds examples from a file to the corresponding vector store (upload only)"""
        table_name = os.path.basename(os.path.dirname(file_path))
        category = os.path.basename(file_path).replace(".txt", "").replace(".json","")
        table_category = f"{table_name}_{category}"

        # Load examples from file
        if file_path.endswith('.txt'):            
            with open(file_path, "r", encoding='utf-8') as f:
                content = f.read()
            examples = content.strip().split("\n")
        elif file_path.endswith('.json'):
            with open(file_path, "r", encoding='utf-8') as f:
                content = json.load(f)
            examples = [json.dumps(example) for example in content]

        # Deduplicate examples
        original_count = len(examples)
        examples = list(dict.fromkeys(examples))
        if len(examples) < original_count:
            print(f"Removed {original_count - len(examples)} duplicate examples from file")

        if self.storage_type == "cloud":
            # Upload to cloud - no local caching
            vector_store = self.create_vector_store(
                table_category, 
                examples, 
                override,
                indexing_strategy=indexing_strategy,
                on_disk=len(examples) > 100000,
                shard_number=2,
                batch_size=batch_size
            )
            if vector_store:
                print(f"✅ Uploaded '{table_category}' to Qdrant cloud")
            return
        
        # For local storage, use traditional FAISS approach
        store_path = os.path.join(self.tables_dir, table_name, table_category)
        if override and os.path.exists(store_path):
            print(f"Removing existing local store at {store_path} (override=True)")
            import shutil
            shutil.rmtree(store_path)
            
        os.makedirs(store_path, exist_ok=True)
        
        # Create and save FAISS store
        vector_store = FAISS.from_texts(examples[:batch_size], self.embeddings)
        for i in range(batch_size, len(examples), batch_size):
            batch = examples[i:i + batch_size]
            vector_store.add_texts(batch)
            print(f"Added batch {i//batch_size + 1}/{(len(examples) + batch_size - 1)//batch_size}")
        
        vector_store.save_local(store_path)
        print(f"✅ Saved local FAISS store '{table_category}'")

    def add_examples_from_directory(self, dir_path: str, override: bool = False, indexing_strategy: IndexingStrategy = IndexingStrategy.DEFAULT, batch_size: int = 100):
        """Adds examples from all files in a directory"""
        collections_to_index = set()
        
        for filename in os.listdir(dir_path):
            if filename.endswith((".txt", ".json")):
                file_path = os.path.join(dir_path, filename)
                table_name = os.path.basename(os.path.dirname(file_path))
                category = os.path.basename(file_path).replace(".txt", "").replace(".json","")
                table_category = f"{table_name}_{category}"
                
                self.add_examples_from_file(file_path, override, indexing_strategy, batch_size)
                
                if indexing_strategy in [IndexingStrategy.FAST, IndexingStrategy.MEMORY_EFFICIENT]:
                    collections_to_index.add(table_category)
        
        # Enable indexing for all collections after bulk upload
        if collections_to_index and self.storage_type == "cloud":
            print("\nEnabling indexing for collections...")
            for collection_name in collections_to_index:
                self.enable_indexing(collection_name)
            print("Indexing enabled for all collections")

    async def search_similar_queries(self, query: str, table_category: str, k: int = 5) -> str:
        """Search for similar queries using on-demand connection - no caching!"""
        
        if table_category not in self.available_categories:
            return f"Error: Category '{table_category}' not found in available categories"
            
        try:
            if self.storage_type == "cloud":
                # Create connection on-demand - don't cache!
                vector_store = QdrantVectorStore(
                    client=self.qdrant_client,
                    collection_name=table_category,
                    embedding=self.embeddings
                )
                
                # Query directly and let it be garbage collected
                results = await vector_store.asimilarity_search(query, k=k)
                
                # Extract content and return immediately
                result_texts = [doc.page_content for doc in results]
                joined_results = '\n'.join(result_texts)
                return f"Tool Response: similar values of {query} in table are:\n{joined_results}"
                
            else:
                # For local storage, use minimal caching
                if table_category not in self.local_stores:
                    self._load_local_store(table_category)
                
                if table_category in self.local_stores:
                    results = await self.local_stores[table_category].asimilarity_search(query, k=k)
                    result_texts = [doc.page_content for doc in results]
                    joined_results = '\n'.join(result_texts)
                    return f"Tool Response: similar values of {query} in table are:\n{joined_results}"
                else:
                    return f"Error: Could not load local store for category '{table_category}'"
                    
        except Exception as e:
            return f"Error during search: {str(e)}"
            
    def _load_local_store(self, table_category: str):
        """Load local FAISS store only if needed"""
        if 'hawkeye' in table_category:
            parts = table_category.split('_')
            table_name = '_'.join(parts[:2])
            category = '_'.join(parts[2:])
        else:
            table_name, category = table_category.split('_', 1)
            
        table_dir = os.path.join(self.tables_dir, table_name)
        store_path = os.path.join(table_dir, table_category)

        if os.path.exists(store_path):
            print(f"Loading local FAISS store '{table_category}'")
            self.local_stores[table_category] = FAISS.load_local(
                store_path, self.embeddings, allow_dangerous_deserialization=True
            )
        else:
            print(f"Warning: No local store found at '{store_path}'")

# Example usage for testing
if __name__ == "__main__":
    async def main():
        vector_store_manager = VectorStoreManager()
        
        # Test memory-efficient search
        # print("Memory usage:", vector_store_manager.get_memory_usage())
        vector_store_manager.add_examples_from_directory(
            "./agents/tables/cricinfo_bbb", 
            override=True,
            indexing_strategy=IndexingStrategy.FAST
        )
        # Test search without caching
        # result = await vector_store_manager.search_similar_queries("virat kohli", "aucb_bbb_player")
        # print("Search result:", result)
        
        # print("Memory usage after search:", vector_store_manager.get_memory_usage())

        
    
    asyncio.run(main())
    