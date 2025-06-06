from typing import List, Literal, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, validator
from agents.utils.vector_stores import VectorStoreManager
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun

# Initialize vector store
vector_store = VectorStoreManager()

# Define valid tables and columns
VALID_TABLES = ['hdata', 'odata_2403','ipl_hawkeye','aucb_bbb']
VALID_TABLE = Literal['hdata','hdata','odata_2403','ipl_hawkeye','aucb_bbb']
VALID_COLUMNS = Literal[
    'player', 'team', 'dismissal', 'ground', 'country', 'competition',
    'bat_hand', 'bowl_style', 'bowl_kind', 'bat_out', 'line', 'length', 'shot','sql_queries'
]

class SearchPair(BaseModel):
    """Schema for individual search criteria"""
    search_value: str = Field( description="Value to search for")
    column_name: str = Field(description="Column to search in")
    table_name: str = Field(description="Table to search in")

class SearchInput(BaseModel):
    """Schema for the search tool input"""
    search_pairs: List[SearchPair] = Field(
        description="List of search criteria. Each criterion should specify search_value, column_name, and table_name"
    )

class SearchTool(BaseTool):
    """Tool for searching the cricket database."""
    
    name: str = "search"
    description: str = """Search for values in specific columns of the cricket database.
"""
    
    args_schema: Type[BaseModel] = SearchInput
    return_direct: bool = False
    
    async def _arun(
        self,
        search_pairs: List[SearchPair],
        limit: int=5,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> list[str]:
        """Execute the search asynchronously, performing validation checks."""
        try:
            print("search_pairs",search_pairs)

            # Proceed with search if validation passes
            results = []
            for pair in search_pairs:
                search_key = f"{pair.table_name}_{pair.column_name}"
                result = await vector_store.search_similar_queries(
                    pair.search_value, 
                    search_key,limit
                )
                results.append(result)
            print(results) # Keep for debugging if needed, consider replacing with logging
            # Ensure consistent return type structure, even if results are complex
            # This might need adjustment depending on what search_similar_queries actually returns
            processed_results = [str(r) for r in results] # Example: convert results to strings
            return processed_results if processed_results else ["No matches found"]
            
        except Exception as e:
            # Log the full exception for debugging
            # Consider more specific error handling if possible
            return [f"Error during search execution: {str(e)}"]

    def _run(
        self,
        search_pairs: List[SearchPair],
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Synchronous version - not implemented."""
        raise NotImplementedError(
            "SearchTool does not support synchronous operations. Use 'arun' instead."
        )

# Create an instance of the tool
tool = SearchTool()