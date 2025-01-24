from ..tools.execute_db import execute_query
import os

def read_schema_columns():
    # Hardcoded list of columns from schema
    return [
        'bat', 'team_bat', 
        'dismissal',
        'ground','country','competition', 'bat_hand',
        'bowl_style', 'bowl_kind', 'bat_out', 
        'line', 'length', 'shot'
    ]

def get_unique_values(column):
    query = f"SELECT DISTINCT {column} FROM adept-cosine-420005.bbbdata.hdata_0510 WHERE {column} IS NOT NULL ORDER BY {column}"
    result = execute_query(query)
    if result['error']:
        print(f"error in column {column}")
        return []
    return result['sql_result'][column].tolist()

def save_values_to_files():
    # Create values directory
    values_dir = "C:\\Users\\adith\\Documents\\Projects\\python-projects\\csql-agent\\agents\\tables\\hdata"    
    os.makedirs(values_dir, exist_ok=True)
    
    # Get columns from schema
    columns = read_schema_columns()
    
    # Get and save unique values for each column
    for column in columns:
        print(f"in {column} file")
        unique_values2=[]
        if column=='bat':
            unique_values2 = get_unique_values('bowl')
        if column=='team_bat':
            unique_values2 = get_unique_values('team_bowl')


        unique_values = get_unique_values(column)
        unique_values = list(set(unique_values2) | set(unique_values))
        mapping= {
            'bat': 'player',
            'team_bat': 'team',
            'dismissal': 'dismissal',
            'ground': 'ground',
            'country': 'country',
            'competition': 'competition',
            'bat_hand': 'bat_hand',
            'bowl_style': 'bowl_style',
            'bowl_kind': 'bowl_kind',
            'bat_out': 'bat_out',
            'line': 'line',
            'length': 'length',
            'shot': 'shot'
        }   
        if unique_values:
            file_path = os.path.join(values_dir, f'{mapping[column]}.txt')
            # Changed to use UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8') as f:
                for value in unique_values:
                    try:
                        f.write(f"{value}\n")
                    except Exception as e:
                        print(f"Error writing value in {column}: {str(e)}")
                        continue

# Initialize by fetching and saving all values
save_values_to_files()