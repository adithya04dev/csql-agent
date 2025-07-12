from ..tools.execute_db import execute_query
import os
from .vector_stores import VectorStoreManager
def read_schema_columns(table_name):
    # Hardcoded list of columns from schema
    if table_name.startswith('hdata') or table_name.startswith('cricinfo'):
        return [
            'bat', 'team_bat', 
            'dismissal',
            'ground','country','competition', 'bat_hand',
            'bowl_style', 'bowl_kind', 
            'line', 'length', 'shot'
        ]
    elif table_name.startswith('odata'):
        return [
            'format', 'ground', 'country',  'battingTeam', 
            'batsman', 'batsmanHand', 'bowlerHand', 'bowlerType', 
            'dismissalType','competition','shot_type', 'variation', 'length',
              'area', 'line', 'foot', 'fielder_action', 
        ]
    elif table_name.startswith('aucb'):
        return [
            'ground','competition', 'battingTeam', 'battingPlayer',  'battingPlayerCountry',
            'dismissalType','fieldingPosition', 'noBallReasonId',
            'battingShotTypeId', 'battingFeetId', 'battingHandId', 
            'bowlingTypeId', 'bowlingFromId', 'bowlingDetailId',
            'appealDismissalTypeId', 'referralOutcomeId',
        ]
    
    elif table_name.startswith('ipl_hawkeye'):
        return [
            'batting_team',  'batsman_name', 
             'delivery_type', 'ball_type', 'shot_type',
            'ball_line', 'ball_length', 'wicket_type', 'ground'
        ]



def get_unique_values(table_name,column):
    query = f"SELECT DISTINCT {column} FROM adept-cosine-420005.bbbdata_csql.{table_name} WHERE {column} IS NOT NULL ORDER BY {column}"
    result = execute_query(query,mode='unique_values')
    if result['error']:
        print(f"error in column {column}")
        return []
    return result['sql_result'][column].tolist()
def save_values_to_files(table_name):
    # Change this from Windows-style absolute path to relative path with forward slashes
    values_dir = os.path.join("./agents/tables", table_name)
    os.makedirs(values_dir, exist_ok=True)
    print(f"table_name: {table_name}")
    
    # Get columns from schema
    columns = read_schema_columns(table_name)
    
    # Get and save unique values for each column
    for column in columns:
        print(f"Processing {column} file")
        unique_values2 = []
        
        # Handle different column mappings based on table type
        if table_name.startswith('hdata') or table_name.startswith('cricinfo'):
            if column == 'bat':
                unique_values2 = get_unique_values(table_name,'bowl')
            elif column == 'team_bat':
                unique_values2 = get_unique_values(table_name,'team_bowl')
        elif table_name.startswith('odata'):
            if column == 'batsman':
                unique_values2 = get_unique_values(table_name,'bowler')
            elif column == 'battingTeam':
                unique_values2 = get_unique_values(table_name,'bowlingTeam')
        elif table_name.startswith('aucb'):
            if column == 'battingTeam':
                unique_values2 = get_unique_values(table_name,'bowlingTeam')
            elif column == 'battingPlayer':
                unique_values2 = get_unique_values(table_name,'bowlingPlayer')

        elif table_name.startswith('ipl_hawkeye'):
            if column == 'batsman_name':
                unique_values2 = get_unique_values(table_name,'bowler_name')
            elif column == 'batting_team':
                unique_values2 = get_unique_values(table_name,'bowling_team')

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
            'odata': {
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
                
            },
            'aucb': {
                'ground': 'ground',
                'competition': 'competition',
                'battingTeam': 'team',
                'battingPlayer': 'player',
                'battingPlayerCountry': 'country',
                'dismissalType': 'dismissalType',
                'fieldingPosition': 'fieldingPosition',
                'noBallReasonId': 'noBallReasonId',
                'battingShotTypeId': 'battingShotTypeId',
                'battingFeetId': 'battingFeetId',
                'battingHandId': 'battingHandId',
                'bowlingTypeId': 'bowlingTypeId',
                'bowlingFromId': 'bowlingFromId',
                'bowlingDetailId': 'bowlingDetailId',
                'appealDismissalTypeId': 'appealDismissalTypeId',
                'referralOutcomeId': 'referralOutcomeId',
            },
            
            'ipl_hawkeye': {
                'batting_team': 'team',
                'batsman_name': 'player',
                'delivery_type': 'delivery_type',
                'ball_type': 'ball_type',
                'shot_type': 'shot_type',
                'ball_line': 'ball_line',
                'ball_length': 'ball_length',
                'wicket_type': 'wicket_type',
                'ground': 'ground'
            }
        }[ 'hdata' if table_name.startswith('hdata') or table_name.startswith('cricinfo') else 'odata' if table_name.startswith('odata') else 'aucb' if table_name.startswith('aucb') else 'ipl_hawkeye' ]

        if unique_values:
            file_path = os.path.join(values_dir, f'{mapping[column]}.txt')
            with open(file_path, 'w', encoding='utf-8') as f:
                for value in unique_values:
                    try:
                        f.write(f"{value}\n")
                    except Exception as e:
                        print(f"Error writing value in {column}: {str(e)}")
                        continue
if __name__ == "__main__":
    # save_values_to_files('aucb_bbb')
    # # Initialize by fetching and saving all values
    # save_values_to_files('cricinfo_bbb')
    save_values_to_files('ipl_hawkeye')
    # save_values_to_files('aucb_bbb')

    # vector_store_manager = VectorStoreManager()
    # vector_store_manager.add_examples_from_directory("./agents/tables/ipl_hawkeye")
    # vector_store_manager.add_examples_from_directory("./agents/tables/hdata")

