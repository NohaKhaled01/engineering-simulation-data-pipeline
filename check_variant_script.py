    # %%
import os
import pandas as pd
import json as js
import re 
from sqlalchemy import create_engine, text

# %%
#Creating connection to mysql database:
engine = create_engine("mysql+pymysql://username:password@localhost:port/db_name")     

# %%
#Pulling Back Variants Table - columns: ID, Title, Abbreviation
variants_in_db = pd.read_sql("SELECT variant_id, Title, variant_abbreviation FROM variant", con=engine)

# %%
folder_path = os.getcwd()

# %%
#Read Current Run Folder Data - thr file:

def runfolder_thr(project_path):
    #Function takes the current folder path, and the current runfolder name, and returns thr and thrmd dfs:
    
    #Initialization:
    thr_file = None

    print('Working on', project_path)
    print('------')
        
    #Get thr file from directory:
    for file in os.listdir(project_path):
        if file.endswith('thr'):
            thr_file = os.path.join(project_path, file)
    
    if not thr_file:
        return('No THR file found. Skipping..') #exits the function
    
    with open (thr_file) as thr_json:
        thr_df = js.load(thr_json)

    return thr_df

# %%
# actual noise words to look for replaced with placeholders, for privacy:
noise = {'noise1', 'noise2', 'noise3', 'noise4', 'noise5'}
matching_score_df = pd.DataFrame(columns = ['project_name', 'variant_name', 'match_score'])

# %%
for runfolder in os.listdir(folder_path):
    project_path = os.path.join(folder_path, runfolder)

    if not os.path.isdir(project_path):
        continue

    thr_df = runfolder_thr(project_path)

    if isinstance (thr_df, str):
        continue

    project_name = thr_df['Name']
    project_variant_abb = project_name[:2]

    if project_variant_abb.isdigit():
        project_name = re.sub(r'^\d+_', '', project_name)
        project_variant_abb = project_name[:2]

    project_tokens = set(re.sub(r'[_\-\s]+', ' ', project_name).lower().split())

    project_tokens -= noise

    variants_filtered = variants_in_db[variants_in_db['variant_abbreviation'].str.contains(project_variant_abb)]
    variants_titles_filtered = list(variants_filtered['Title'])
    matching_score_df.at[runfolder, 'project_name'] = project_name
    highest_match = 0

    for variant in range(len(variants_titles_filtered)):
        variant_name = variants_titles_filtered[variant]
        variant_tokens = set(re.sub(r'[_\-\s]+', ' ', variant_name).lower().split())
        variant_tokens -= noise

        match = variant_tokens.intersection(project_tokens)
        match_score = len(match)/len(variant_tokens)
        
        if match_score > highest_match:
            highest_variant = variant_name
            highest_match = match_score

    matching_score_df.at[runfolder, 'variant_name'] = highest_variant
    matching_score_df.at[runfolder, 'match_score'] = highest_match

# %%
matching_score_df.to_csv('matching_score.csv', index=False)




