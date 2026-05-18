# %%
import os
import pandas as pd
import json as js
from thefuzz import fuzz, process
from sqlalchemy import create_engine, text

# %%
#Creating connection to mysql database:
engine = create_engine("mysql+pymysql://username:password@localhost:port/db_name")

# %%
#Pulling Back Variants Table - columns: ID, Title, Abbreviation
variants_in_db = pd.read_sql("SELECT variant_id, Title, variant_abbreviation FROM variant", con=engine)

# %%
#Pulling Back Components Table - columns: all
components_in_db = pd.read_sql("SELECT * FROM components", con=engine)

# %%
#Getting All the Project Names as a list:
project_names = set(components_in_db['project_name'])

# %%
project_names_list = list(project_names)

# %% [markdown]
# #### Matching_df as the mapping df:
# ##### project name - to match with components/exhaust table.
# ##### picker variant title - to match with variants table.
# ##### match score - to check the table before moving it.
# 

# %%
column_names = ['project_name', 'picked_variant_title', 'match_score']
matching_df = pd.DataFrame(columns = column_names)

# %%
def matching_project(projects, variants):
    #Function takes in the project names, and the variants df, and returns the matching df

    column_names = ['project_name', 'picked_variant_title', 'match_score']
    matching_df_sub = pd.DataFrame(columns = column_names)

    for project in range(len(projects)):
        search_for_project = projects[project] #project to be searched for

        project_variant_abb = search_for_project[:2] #abbreviation to limit the search to
        
        if project_variant_abb.isdigit():
            print('Skipping ', search_for_project, '. Project name starts with a number!')
            continue

        #filtered variant df:
        variants_filtered = variants[variants['variant_abbreviation'].str.contains(project_variant_abb)]
        variants_titles_filtered = list(variants_filtered['Title'])
    
        picked_variant_title, match_score = process.extractOne(search_for_project, variants_titles_filtered, scorer = fuzz.token_set_ratio)
        
        print("Project:", search_for_project, "- matched with variant:", picked_variant_title)

        matching_df_sub.loc[project, 'project_name'] = search_for_project
        
        matching_df_sub.loc[project, ['picked_variant_title', 'match_score']] = picked_variant_title, match_score

    return matching_df_sub

# %%
#Calling the function:
matching_df = matching_project(project_names_list, variants_in_db)

# %%
#Exporting the matching df to check the matching externally:
matching_df.to_csv(r'matching_df.csv', index = False)

# %%
component_df_mid = pd.merge(components_in_db, matching_df, how = 'left', on = 'project_name')

# %%
component_df_mid = component_df_mid.drop(columns = ['variant_id', 'match_score'])

# %% [markdown]
# ##### Merging component_df_mid and variants_in_db:
# result: component id -- project name -- component name -- picked variant title -- variant id -- title -- variant abbreviation

# %%
components_df = pd.merge(component_df_mid, variants_in_db, how = 'inner', left_on = 'picked_variant_title', right_on = 'Title')

# %%
components_df = components_df.drop(columns = ['picked_variant_title', 'Title', 'variant_abbreviation'])

# %% [markdown]
# ##### Update the variant id column in the components table back in the db:

# %%
#Instead of pushing back to the same table and having duplicate values - ones with variant id and ones without,
#And instead of pushing back to a new table
#The empty variant id column in the current table will be just updated ..

with engine.connect() as conn:
    for _, row in components_df.iterrows(): #iterrows returns index and row .. so have to use _ for the unused index
        conn.execute(
                                text(""" 
                                    UPDATE components
                                    SET variant_id = :variant_place_holder
                                    WHERE component_id = :component_place_holder
                                    """), 
                                    {
                                    'variant_place_holder': row['variant_id'],
                                    'component_place_holder': row['component_id']
                                    }
                                )
    conn.commit()





