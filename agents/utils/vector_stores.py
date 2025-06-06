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
        
        # Initialize Qdrant client if using cloud storage
        if self.storage_type == "cloud":
            try:
                self.qdrant_url = os.getenv("QDRANT_URL")
                self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
                
                if not self.qdrant_url or not self.qdrant_api_key:
                    print("Warning: QDRANT_URL or QDRANT_API_KEY not set. Falling back to local storage.")
                    self.storage_type = "local"
                else:
                    self.qdrant_client = QdrantClient(
                        url=self.qdrant_url,
                        api_key=self.qdrant_api_key,
                        timeout=60,  # Increase timeout to 60 seconds for operations
                        prefer_grpc=True  # Use gRPC for better performance
                    )
                    print(f"Connected to Qdrant cloud at {self.qdrant_url}")
            except Exception as e:
                print(f"Error connecting to Qdrant cloud: {str(e)}. Falling back to local storage.")
                self.storage_type = "local"

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

    def create_vector_store(
        self, 
        collection_name: str, 
        texts: Optional[List[str]] = None, 
        override: bool = False,
        indexing_strategy: IndexingStrategy = IndexingStrategy.DEFAULT,
        on_disk: bool = False,
        shard_number: Optional[int] = None,
        batch_size: int = 100  # Add batch size parameter
    ) -> QdrantVectorStore:
        """
        Create a new vector store collection in Qdrant with proper configuration.
        
        Args:
            collection_name: Name of the collection to create
            texts: Optional list of initial texts to add to the collection
            override: If True, recreates the collection even if it exists
            indexing_strategy: Strategy for indexing (FAST, MEMORY_EFFICIENT, or DEFAULT)
            on_disk: If True, stores vectors directly on disk instead of RAM
            shard_number: Number of shards for parallel upload (2-4 recommended per machine)
            batch_size: Number of texts to process in each batch (default 100)
            
        Returns:
            QdrantVectorStore: The created vector store
        """
        try:
            # If override is True, ensure we delete any existing collection first
            if override:
                try:
                    print(f"Forcing deletion of collection '{collection_name}' (override=True)")
                    self.qdrant_client.delete_collection(collection_name)
                    # Wait a moment to ensure deletion is processed
                    time.sleep(1)
                except Exception as e:
                    print(f"Note: Collection deletion attempt: {str(e)}")
            
            # Prepare configuration based on indexing strategy
            hnsw_config = None
            optimizer_config = None
            
            if indexing_strategy == IndexingStrategy.FAST:
                # Disable indexing for fastest upload
                optimizer_config = OptimizersConfigDiff(indexing_threshold=0)
            elif indexing_strategy == IndexingStrategy.MEMORY_EFFICIENT:
                # Defer HNSW graph construction
                hnsw_config = HnswConfigDiff(m=0)
            
            # Check if collection exists
            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
                
                # If we reach here and override was True, something went wrong with deletion
                if override:
                    print(f"Warning: Failed to delete collection. Attempting recreation...")
                    self.qdrant_client.delete_collection(collection_name)
                    raise Exception("Forcing recreation after failed deletion")
                    
                print(f"Collection '{collection_name}' already exists")
                    
                # Verify vector configuration
                if collection_info.config.params.vectors.size != self.embedding_size:
                    print(f"Recreating collection '{collection_name}' with correct vector size")
                    self.qdrant_client.delete_collection(collection_name)
                    raise Exception("Collection needs recreation")
                    
            except Exception as e:
                print(f"Creating new collection '{collection_name}'")
                # Create new collection with proper configuration
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_size,
                        distance=Distance.COSINE,
                        on_disk=on_disk  # Enable direct disk storage if requested
                    ),
                    hnsw_config=hnsw_config,  # Apply HNSW configuration if set
                    optimizers_config=optimizer_config,  # Apply optimizer configuration if set
                    shard_number=shard_number,  # Set number of shards if specified
                )
            
            # Create vector store
            vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=collection_name,
                embedding=self.embeddings
            )
            
            # Add initial texts in batches if provided
            if texts:
                # Deduplicate texts first
                unique_texts = list(set(texts))
                if len(unique_texts) < len(texts):
                    print(f"Removed {len(texts) - len(unique_texts)} duplicate texts")
                
                total_texts = len(unique_texts)
                for i in range(0, total_texts, batch_size):
                    batch = unique_texts[i:i + batch_size]
                    vector_store.add_texts(batch)
                    print(f"Added batch {i//batch_size + 1}/{(total_texts + batch_size - 1)//batch_size} "
                          f"({len(batch)} texts) to collection '{collection_name}'")

            # If using FAST strategy, we'll need to enable indexing later
            if indexing_strategy == IndexingStrategy.FAST:
                print("Note: Indexing is disabled for fast upload. Enable it later using enable_indexing()")
            elif indexing_strategy == IndexingStrategy.MEMORY_EFFICIENT:
                print("Note: HNSW graph construction is deferred. Enable it later using enable_indexing()")
                
            return vector_store
            
        except Exception as e:
            print(f"Error with vector store: {str(e)}")
            return None

    def enable_indexing(self, collection_name: str, indexing_threshold: int = 20000, m: int = 16):
        """
        Enable indexing for a collection after bulk upload.
        
        Args:
            collection_name: Name of the collection
            indexing_threshold: Threshold for indexing (default 20000)
            m: HNSW graph parameter (default 16)
        """
        try:
            # Enable indexing threshold
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

    def load_store(self, table_category: str):
        """Load a specific vector store on demand"""
        if table_category in self.stores:
            return self.stores[table_category]
            
        if table_category not in self.available_categories:
            print(f"Warning: Category '{table_category}' not found in available categories.")
            return None

        # For cloud storage, just connect to existing collection
        if self.storage_type == "cloud":
            try:
                print(f"Connecting to existing collection '{table_category}'")
                vector_store = QdrantVectorStore(
                    client=self.qdrant_client,
                    collection_name=table_category,
                    embedding=self.embeddings
                )
                self.stores[table_category] = vector_store
                self.retrievers[table_category] = vector_store.as_retriever(search_kwargs={"k": 5})
                return self.stores[table_category]
            except Exception as e:
                print(f"Error connecting to collection: {str(e)}")
                return None

        # For local storage, load from disk
        if 'hawkeye' in table_category:
            parts = table_category.split('_')
            table_name = '_'.join(parts[:2])  # 'ipl_hawkeye'
            category = '_'.join(parts[2:])    # 'delivery_type' or whatever comes after
        else:
            table_name, category = table_category.split('_', 1)
            
        table_dir = os.path.join(self.tables_dir, table_name)
        store_path = os.path.join(table_dir, table_category)

        if os.path.exists(store_path):
            self.stores[table_category] = FAISS.load_local(
                store_path, self.embeddings, allow_dangerous_deserialization=True
            )
            self.retrievers[table_category] = self.stores[table_category].as_retriever(search_kwargs={"k": 5})
            return self.stores[table_category]
        else:
            print(f"Warning: No local store found at '{store_path}'")
            return None

    def add_examples_from_file(self, file_path: str, override: bool = False, indexing_strategy: IndexingStrategy = IndexingStrategy.DEFAULT, batch_size: int = 100):
        """
        Adds examples from a .txt file to the corresponding vector store.
        
        Args:
            file_path: Path to the file containing examples
            override: If True, recreates the collection even if it exists
            indexing_strategy: Strategy for indexing during bulk upload
            batch_size: Number of examples to process in each batch
        """
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
        examples = list(dict.fromkeys(examples))  # Preserves order while removing duplicates
        if len(examples) < original_count:
            print(f"Removed {original_count - len(examples)} duplicate examples from file")

        # If override=True, completely remove existing collection
        if override and table_category in self.stores:
            print(f"Removing store for {table_category} from memory (override=True)")
            if table_category in self.retrievers:
                del self.retrievers[table_category]
            del self.stores[table_category]

        # Create or get the store
        if table_category not in self.stores:
            if self.storage_type == "cloud":
                # Use 2 shards for parallel upload and on_disk for large datasets
                vector_store = self.create_vector_store(
                    table_category, 
                    examples, 
                    override,
                    indexing_strategy=indexing_strategy,
                    on_disk=len(examples) > 100000,  # Use on_disk for large datasets
                    shard_number=2,  # Use 2 shards for parallel upload
                    batch_size=batch_size  # Pass batch size
                )
                if vector_store:
                    self.stores[table_category] = vector_store
                    self.retrievers[table_category] = vector_store.as_retriever(search_kwargs={"k": 5})
                    return
            
            # Fall back to local storage
            store_path = os.path.join(self.tables_dir, table_name, table_category)
            if override and os.path.exists(store_path):
                print(f"Removing existing local store at {store_path} (override=True)")
                import shutil
                shutil.rmtree(store_path)
                
            os.makedirs(store_path, exist_ok=True)
            
            # Process in batches for local storage too
            self.stores[table_category] = FAISS.from_texts(examples[:batch_size], self.embeddings)
            
            # Add remaining examples in batches
            for i in range(batch_size, len(examples), batch_size):
                batch = examples[i:i + batch_size]
                self.stores[table_category].add_texts(batch)
                print(f"Added batch {i//batch_size + 1}/{(len(examples) + batch_size - 1)//batch_size} "
                      f"({len(batch)} texts) to local store")
            
            self.stores[table_category].save_local(store_path)
            self.retrievers[table_category] = self.stores[table_category].as_retriever(search_kwargs={"k": 5})

    def add_examples_from_directory(self, dir_path: str, override: bool = False, indexing_strategy: IndexingStrategy = IndexingStrategy.DEFAULT, batch_size: int = 100):
        """
        Adds examples from all .txt files in a directory.
        
        Args:
            dir_path: Path to directory containing example files
            override: If True, recreates collections even if they exist
            indexing_strategy: Strategy for indexing during bulk upload
            batch_size: Number of examples to process in each batch
        """
        collections_to_index = set()  # Keep track of collections that need indexing enabled
        
        for filename in os.listdir(dir_path):
            print("adding file name", filename)
            if filename.endswith(".txt") or filename.endswith(".json"):
                file_path = os.path.join(dir_path, filename)
                table_name = os.path.basename(os.path.dirname(file_path))
                category = os.path.basename(file_path).replace(".txt", "").replace(".json","")
                table_category = f"{table_name}_{category}"
                
                self.add_examples_from_file(file_path, override, indexing_strategy, batch_size)
                
                # Track collections that need indexing enabled
                if indexing_strategy in [IndexingStrategy.FAST, IndexingStrategy.MEMORY_EFFICIENT]:
                    collections_to_index.add(table_category)
        
        # Enable indexing for all collections after bulk upload
        if collections_to_index and self.storage_type == "cloud":
            print("\nEnabling indexing for collections...")
            for collection_name in collections_to_index:
                print(f"Enabling indexing for {collection_name}")
                self.enable_indexing(collection_name)
            print("Indexing enabled for all collections")

    async def search_similar_queries(self, query: str, table_category: str, k: int = 5) -> str:
        """Search for similar queries in a specific category's vector store"""
        # Just load the store if not already loaded - don't recreate or add texts
        if table_category not in self.stores:
            store = self.load_store(table_category)
            if not store:
                return f"Error: Could not load store for category '{table_category}'"
            
        retriever = self.retrievers.get(table_category)
        if not retriever:
            return f"Error: No retriever found for category '{table_category}'"

        results = await retriever.ainvoke(query)
        
        # Collect results in a list first
        result_texts = [doc.page_content for doc in results[:k]]
        
        # Join them together in one operation
        return f"Tool Response: similar values of {query} in table are:\n{'\n'.join(result_texts)}"

# Example Usage
if __name__ == "__main__":
    
    # vector_store_manager.add_examples_from_directory("agents/tables/ipl_hawkeye")
    # vector_store_manager.add_examples_from_directory("./agents/tables/hdata")
    
    async def main():
        import asyncio
        
        vector_store_manager = VectorStoreManager()
# Fast upload (high RAM usage)
# Fast upload with automatic indexing
        # vector_store_manager.add_examples_from_directory(
        #     "./agents/tables/hdata", 
        #     override=True,
        #     indexing_strategy=IndexingStrategy.FAST
        # )

        # Memory efficient mode with automatic indexing
        # vector_store_manager.add_examples_from_directory(
        #     "./agents/tables/ipl_hawkeye", 
        #     override=True,

        #     indexing_strategy=IndexingStrategy.MEMORY_EFFICIENT
        # )
        # vector_store_manager.add_examples_from_directory(
        #     "./agents/tables/aucb_bbb", 
        #     override=True,
        #     indexing_strategy=IndexingStrategy.FAST
        # )

        
        # print(vector_store_manager.available_categories)
        # vector_store_manager.add_examples_from_directory("./agents/tables/ipl_hawkeye", override=True)
        # vector_store_manager.add_examples_from_directory("./agents/tables/hdata", override=True)

        # print(await vector_store_manager.search_similar_queries("v kohli", "aucb_bbb_player"))
        # print(await vector_store_manager.search_similar_queries("ipl", "aucb_bbb_competition"))
        # print(await vector_store_manager.search_similar_queries("bharat", "aucb_bbb_country"))
        # print(await vector_store_manager.search_similar_queries("Indian premier league", "hdata_competition"))
        # print(await vector_store_manager.search_similar_queries("virat kohli", "hdata_player"))
        # print(await vector_store_manager.search_similar_queries("v kohli", "hdata_player"))
        # print(await vector_store_manager.search_similar_queries("bumrah toe crusher", "hdata_length"))
        # print(await vector_store_manager.search_similar_queries("kohi", "ipl_hawkeye_player"))
        # print(await vector_store_manager.search_similar_queries("back length", "ipl_hawkeye_ball_length"))
        # print(await vector_store_manager.search_similar_queries("ipl 2024", "hdata_2403_competition"))
    
    asyncio.run(main())