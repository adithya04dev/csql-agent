import re

async def parse_sql_query(query):
    # Find all SQL code blocks in the query
    sql_matches = re.findall(r'```sql\n(.*?)```', query, re.DOTALL)
    
    # Return the last match if any matches exist
    if sql_matches:
        return sql_matches[-1].strip()
    
    return ''