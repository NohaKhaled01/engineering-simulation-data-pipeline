# %%
import os
import pandas as pd
import json as js
from sqlalchemy import create_engine, text

# %%
#Creating connection to mysql database:
engine = create_engine("mysql+pymysql://username:password@localhost:port/db_name")

# %%
#path with runfolders to run script on - if running a script in terminal:
current_dir = os.getcwd()
folder_path = current_dir


# %%
def extract_components_materials(thrmd_df, thr_df):
    #function used to populate the component df and material df:
    material_df = pd.DataFrame(columns = ['source_project_name', 'component_name', 'solid_name', 'solid_material'])
    material_row = 0
    
    for comp in range(len(thrmd_df['Geometry']['Components'])):
        #number of regions in component
        no_of_regions = len(thrmd_df['Geometry']['Components'][comp]['MeshInput']['Mesh']['Regions']) 

        for region in range(no_of_regions):
            #project name for each solid in each component:
            material_df.loc[material_row, 'source_project_name'] = thr_df['Name']

            #component name - to be able to connect the two dfs later:
            material_df.loc[material_row, 'component_name'] = thrmd_df['Geometry']['Components'][comp]['OwnerLabel']['Label']

            #region names inside component:
            material_df.loc[material_row, 'solid_name'] = thrmd_df['Geometry']['Components'][comp]['MeshInput']['Mesh']['Regions'][region]['UserLabel']

            #material for each region:
            material_df.loc[material_row, 'solid_material'] = thrmd_df['Geometry']['Components'][comp]['MeshInput']['Mesh']['Regions'][region]['CustomMaterial']['Value']

            material_row += 1

    return material_df


# %%
for runfolder in os.listdir(folder_path):
    #runfolder path:
    project_path = os.path.join(folder_path, runfolder)
    thr_file = None #initialized as None incase a runfolder has no thr or thrmd
    thrmd_file = None #initialized as None incase a runfolder has no thr or thrmd

    #a quick check: is the path a directory [folder]? if not, continue to the next runfolder.
    if not os.path.isdir(project_path):
        print("Not a directory/folder - ", project_path, ". Skipping.") 
        continue

    #get the thr and thrmd file paths - loop over the files in the runfolder:
    #thr file:
    for file in os.listdir(project_path):
        if file.endswith('thr'):
            thr_file = os.path.join(project_path, file)

    #thrmd file:
    module_path = os.path.join(project_path, 'Modules')
    if os.path.isdir(module_path):
        for file in os.listdir(module_path):
            if file.endswith('thrmd'):
                thrmd_file = os.path.join(module_path, file)
    else:
        print("Not a runfolder - ", project_path, ". Skipping.")
        continue

    #If either thr or thrmd are missing from runfolder, print error and continue to the next runfolder:
    if not thr_file:
        print('THR missing - ', project_path, ". Skipping")
        continue
    elif not thrmd_file:
        print('THRMD missing - ', project_path, ". Skipping")
        continue

    ## Now we have the paths for the thr and thrmd files. Time to import them and do the usual work:
    with open (thr_file) as thr_json:
        thr_df = js.load(thr_json)
    with open (thrmd_file) as thrmd_json:
        thrmd_df = js.load(thrmd_json)

    #Get names of runfolders in db already:
    runfolder_names_in_db = pd.read_sql("SELECT DISTINCT project_name FROM components_materials", con=engine)
    
    #Check if current runfolder is already in database:
    project_name = thr_df['Name']

    if project_name in runfolder_names_in_db.values:
        print('Already in database - ', project_name, '. Skipping.')
        continue

     #component_material_df - contains regions and their materials + component name, to be connected to the component df later
    column_names_materials = ['source_project_name', 'component_name', 'solid_name', 'solid_material']
    component_material_df = pd.DataFrame(columns = column_names_materials)

    #Calling the function to extract data from the thr and thrmd:
    df_1 = extract_components_materials(thrmd_df, thr_df)

    component_material_df = pd.concat([component_material_df, df_1])

    #Pull Components table from DB for Primary Key:
    components_in_db = pd.read_sql("SELECT component_id, source_project_name, component_name FROM components", con=engine)

    #Merge two dfs:
    component_material_df = component_material_df.merge(components_in_db, on = ['source_project_name', 'component_name'], how = 'left')

    #Clean Materials df:
    component_material_df = component_material_df.drop(columns = 'source_project_name')

    #Push Materials to MYSQL:
    component_material_df.to_sql('components_materials', con=engine, if_exists='append', index=False)
    print("Components Materials pushed to MySQL")

    print("✅ ", project_path, " Done importing materials for components! Moving onto next!")





