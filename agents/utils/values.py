from ..tools.execute_db import execute_query
import os

def read_schema_columns(table_name):
    # Hardcoded list of columns from schema
    if table_name.startswith('hdata'):
        return [
            'bat', 'team_bat', 
            'dismissal',
            'ground','country','competition', 'bat_hand',
            'bowl_style', 'bowl_kind', 'bat_out', 
            'line', 'length', 'shot'
        ]
    else:
        return [
            'format', 'ground', 'country',  'battingTeam', 
            'batsman', 'batsmanHand', 'bowlerHand', 'bowlerType', 
            'dismissalType','competition','shot_type', 'variation', 'length',
              'area', 'line', 'foot', 'fielder_action', 
        ]


def get_unique_values(table_name,column):
    query = f"SELECT DISTINCT {column} FROM adept-cosine-420005.bbbdata.{table_name} WHERE {column} IS NOT NULL ORDER BY {column}"
    result = execute_query(query)
    if result['error']:
        print(f"error in column {column}")
        return []
    return result['sql_result'][column].tolist()
def save_values_to_files(table_name):
    # Create values directory based on table name
    values_dir = os.path.join("C:\\Users\\adith\\Documents\\Projects\\python-projects\\csql-agent\\agents\\tables", table_name)
    os.makedirs(values_dir, exist_ok=True)
    
    # Get columns from schema
    columns = read_schema_columns(table_name)
    
    # Get and save unique values for each column
    for column in columns:
        print(f"Processing {column} file")
        unique_values2 = []
        
        # Handle different column mappings based on table type
        if table_name.startswith('hdata'):
            if column == 'bat':
                unique_values2 = get_unique_values(table_name,'bowl')
            elif column == 'team_bat':
                unique_values2 = get_unique_values(table_name,'team_bowl')
        else:
            if column == 'batsman':
                unique_values2 = get_unique_values(table_name,'bowler')
            elif column == 'battingTeam':
                unique_values2 = get_unique_values(table_name,'bowlingTeam')

        unique_values = get_unique_values(table_name,column)
        unique_values = list(set(unique_values2) | set(unique_values))
        
        # Create appropriate mapping based on table type
        mapping = {
            'hdata': {
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
            },
            'other': {
                'batsman': 'player',
                'battingTeam': 'team',
                'dismissalType': 'dismissal',
                'ground': 'ground',
                'country': 'country',
                'competition': 'competition',
                'batsmanHand': 'batsmanHand',
                'bowlerType': 'bowlerType',
                'bowlerHand': 'bowlerHand',
                'shot_type': 'shot_type',
                'line': 'line',
                'length': 'length',
                'format': 'format',
                 'area': 'area',  
              'foot': 'foot',
                'fielder_action': 'fielder_action', 
                'variation': 'variation',
                
            }
        }[ 'hdata' if table_name.startswith('hdata') else 'other' ]

        if unique_values:
            file_path = os.path.join(values_dir, f'{mapping[column]}.txt')
            with open(file_path, 'w', encoding='utf-8') as f:
                for value in unique_values:
                    try:
                        f.write(f"{value}\n")
                    except Exception as e:
                        print(f"Error writing value in {column}: {str(e)}")
                        continue

# Initialize by fetching and saving all values
# save_values_to_files('hdata_2403')
save_values_to_files('odata_2403')