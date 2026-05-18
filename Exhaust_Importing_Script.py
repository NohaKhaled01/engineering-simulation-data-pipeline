# %%
import os
import pandas as pd
import json as js
from thefuzz import fuzz, process
from sqlalchemy import create_engine, text
import re

# %%
#Creating connection to mysql database:
engine = create_engine("mysql+pymysql://username:password@localhost:port/db_name")

# %%
#path with runfolders to run script on:
folder_path = os.getcwd()

# %%
# Exhaust Naming Pattern:
exh_pattern = r'Exhaust|exhaust|exh|Exh'
# Sync Naming Patterns — update these to match your project naming conventions
sync_pattern = r"(Step\s[C]\/Sync\s\d|P?o?s?t?\-?Sync\s?\w?X?1?\+?\+?\+?|Step\s?\w|TYPE_1|TYPE_2|TYPE_3)"
sync_pattern_2 = r"(MARKET_A\sw\.\sMARKET_B\sExhaust|MARKET_A|MARKET_B)"
sync_number_pattern = r'(\d.{0,5}|TYPE_1|TYPE_2|TYPE_3)'


# %%
# Data from DB:

syncs_in_db = pd.read_sql("SELECT sync_id, variant_id, sync_title, sync_name FROM sync", con=engine)
variants_in_db = pd.read_sql("SELECT variant_id, title, variant_abbreviation FROM variant", con=engine)

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
#Read Current Run Folder Data - thrmd file:

def runfolder_thrmd(project_path):
    #Function takes the current folder path, and the current runfolder name, and returns thr and thrmd dfs:
    
    #Initialization:
    thrmd_file = None
    
    module_path = os.path.join(project_path, 'Modules')
    if not os.path.exists(module_path):
        return('No Modules folder found. Skipping ..')
        
    for file in os.listdir(module_path):
        if file.endswith('thrmd'):
            thrmd_file = os.path.join(module_path, file)
    
    if not thrmd_file:
        return('No THRMD file found inside Modules. Skipping ..')
    
    with open (thrmd_file) as thrmd_json:
        thrmd_df = js.load(thrmd_json)

    return thrmd_df

# %%
#Extracting exhaust segment meshes - to be run on current project:

def extract_exh_meshes(thr_df, thrmd_df):
    #Functions takes the thr and thrmd, and returns the mesh files names for the segments in the exhaust flowline
    
    meshes_columns = ['project_name', 'segment_name', 'mesh_file_name']
    current_exhaust_meshes_df = pd.DataFrame(columns = meshes_columns)

    #Making sure to get the exhaust flowline, and not any other flowline that could be there:
    for flowline_num in range(len(thrmd_df['Geometry']['FlowLines'])):
        flowline_label = thrmd_df['Geometry']['FlowLines'][flowline_num]['Label']

        flowline = flowline_num

        search_result = re.search(exh_pattern, flowline_label) #does flowline label match exh pattern?

        if search_result: #if true, get out of the for loop and continue the function. if false, keep searching
            break

    if not search_result: #no exhaust flowlines found
        return None, None
    
    no_of_segments = len(thrmd_df['Geometry']['FlowLines'][flowline]['Segments']) #number of segments in flow line 

    for segment in range(no_of_segments):
        #project name:
        current_exhaust_meshes_df.loc[segment, 'project_name'] = thr_df['Name']
        #segment name:
        current_exhaust_meshes_df.loc[segment, 'segment_name'] = thrmd_df['Geometry']['FlowLines'][flowline]['Segments'][segment]['Label']
        #mesh file name for each segment:
        current_exhaust_meshes_df.loc[segment, 'mesh_file_name'] = thrmd_df['Geometry']['FlowLines'][flowline]['Segments'][segment]['Mesh']['File']

    return current_exhaust_meshes_df, flowline

# %%
# Compare exhaust meshes to ones already in DB:

def compare_meshes(project_1_meshes, exhaust_meshes_in_db):
    #Function takes current project meshes, and exhaust meshes from db, and returns similar_exhausts variable
    #If similar_exhausts = 1 -- dont import current project
    #If similar_exhausts = 0 -- import current project
    
    #the ids in the meshes db .. every id is a new project
    project_name_ids = exhaust_meshes_in_db['project_name_id'].unique().tolist() 

    similar_exhausts = 0
    for project_id in project_name_ids:
        #create a small df with the meshes for the current project id:
        exhaust_meshes_1 = exhaust_meshes_in_db[exhaust_meshes_in_db['project_name_id'] == project_id]

        if len(project_1_meshes) != len(exhaust_meshes_1):
            print(project_1_meshes.iloc[0]['project_name'], 'has different meshes number than ', exhaust_meshes_1.iloc[0]['project_name'], 'with project id', project_id)

        elif (~project_1_meshes['mesh_file_name'].isin(exhaust_meshes_1['mesh_file_name'])).any(): #true if different, false if similar
            print(project_1_meshes.iloc[0]['project_name'], 'has different mesh file names', exhaust_meshes_1.iloc[0]['project_name'], 'with project id', project_id)

        else:
            similar_exhausts = 1
            print(project_1_meshes.iloc[0]['project_name'], 'has same number of segments, and same mesh file names as ', exhaust_meshes_1.iloc[0]['project_name'], 'with project id', project_id)
            return similar_exhausts

    return similar_exhausts

# %%
# Extracting exhaust segments data - to be used later in exhaust boolean function:

def extract_exh_data(thrmd_df, thr_df, flowline):
    #Function takes in thr and thrmd dfs
    #Returns two dfs - segments df, and materials df
    
    exhaust_segments_df = pd.DataFrame(columns = ['project_name', 'segment_name'])
    exhaust_material_df = pd.DataFrame(columns = ['segment_name', 'segment_region_name', 'segment_region_material'])
    material_row = 0

    no_of_segments = len(thrmd_df['Geometry']['FlowLines'][flowline]['Segments']) #number of segments in flow line

    for segment in range(no_of_segments):
        #project name for exhaust:
        exhaust_segments_df.loc[segment, 'project_name'] = thr_df['Name']

        #segment name:
        exhaust_segments_df.loc[segment, 'segment_name'] = thrmd_df['Geometry']['FlowLines'][flowline]['Segments'][segment]['Label']

        #number of regions in each segment:
        no_of_regions = len(thrmd_df['Geometry']['FlowLines'][flowline]['Segments'][segment]['Mesh']['Regions'])

        for region in range(no_of_regions):
            #project name for exhaust:
            exhaust_material_df.loc[material_row, 'project_name'] = thr_df['Name']

            #segment name:
            exhaust_material_df.loc[material_row, 'segment_name'] = thrmd_df['Geometry']['FlowLines'][flowline]['Segments'][segment]['Label']

            #region name in segment:
            exhaust_material_df.loc[material_row, 'segment_region_name'] = thrmd_df['Geometry']['FlowLines'][flowline]['Segments'][segment]['Mesh']['Regions'][region]['Label']

            #region material:
            exhaust_material_df.loc[material_row, 'segment_region_material'] = thrmd_df['Geometry']['FlowLines'][flowline]['Segments'][segment]['Mesh']['Regions'][region]['CustomMaterial']['Value']
            
            material_row += 1

    exhaust_segments_df['has_manifold'] = exhaust_segments_df['segment_name'].str.contains(r'Manifold|Mani|Man|Mainfold', case = False)
    exhaust_segments_df['has_turbine'] = exhaust_segments_df['segment_name'].str.contains(r'Turbine|Turbo|TUB?R?', case = False)
    #exhaust_segments_df['has_cross_pipe'] = exhaust_segments_df['segment_name'].str.contains('cross', case = False)
    exhaust_segments_df['has_rear_CAT'] = exhaust_segments_df['segment_name'].str.contains(r'RR\_?\s?CAT|Rear\_?\s?CAT', case = False, regex = True)
    exhaust_segments_df['has_muffler'] = exhaust_segments_df['segment_name'].str.contains(r'Muffl?e?r?', case = False)
    exhaust_segments_df['has_resonator'] = exhaust_segments_df['segment_name'].str.contains(r'Resonator|Reso?n?', case = False)
    exhaust_segments_df['has_dual_turbine'] = exhaust_segments_df['segment_name'].str.contains(r'Turbine_+|Turbo_+|LFT_Turbine|LFT_Turbo|Left_Turbine|Left_Turbo|RGT_Turbine|RGT_Turbo|Right_Turbine|Right_Turbo', case = False)
    exhaust_segments_df['has_flex_joint'] = exhaust_segments_df['segment_name'].str.contains(r'Flex', case = False)
    exhaust_segments_df['has_dual_end'] = exhaust_segments_df['segment_name'].str.contains(r'Tailpipe_+|Left_TailPipe|Right_TailPipe|LFT_TailPipe|RGT_TailPipe', case = False)
    exhaust_segments_df['has_y_joint'] = exhaust_segments_df['segment_name'].str.contains(r'Y\_?\s?Pipe|Y\_?\s?Joint+', case = False)
    exhaust_segments_df['has_SCR_or_DPF_or_GPF'] = exhaust_segments_df['segment_name'].str.contains(r'SCR|DPF|GPF', case = False)

    return exhaust_segments_df, exhaust_material_df

# %%
# Bool Checks function
def exh_bool (exhaust_segments_df):
    # Function takes the exhaust segments df and returns a df with boolean checks for each exhaust record
    # One exhaust record per exhaust
    
    exhaust_df = pd.DataFrame([{
    'project_name':    exhaust_segments_df['project_name'].iloc[0],
    'has_manifold':    exhaust_segments_df['has_manifold'].any(),
    'has_turbine':       exhaust_segments_df['has_turbine'].any(),
    'has_dual_turbine':   exhaust_segments_df['has_dual_turbine'].any(),
    'has_rear_CAT':   exhaust_segments_df['has_rear_CAT'].any(),
    'has_flex_joint':   exhaust_segments_df['has_flex_joint'].any(),
    'has_y_joint':   exhaust_segments_df['has_y_joint'].any(),   
    'has_muffler':     exhaust_segments_df['has_muffler'].any(),
    'has_resonator':   exhaust_segments_df['has_resonator'].any(),
    'has_dual_end':     exhaust_segments_df['has_dual_end'].any(),
    'has_SCR_or_DPF_or_GPF':   exhaust_segments_df['has_SCR_or_DPF_or_GPF'].any()
    }])
    
    return exhaust_df

# %%
# Connect exhaust to sync id function
def exhaust_2_sync(exhaust_df, thr_df, variants_in_db, syncs_in_db):
    # Function takes in the thr, exhaust df, variants and syncs table in the DB
    # Returns updated exhaust df with the sync id for each exhaust id
    current_project = thr_df['Name']
    project_variant = current_project[:2]

    current_project_cleaned = current_project
    
    if project_variant.isdigit():
        current_project_cleaned = re.sub(r'^\d+_', '', current_project)
        project_variant = current_project_cleaned[:2]

    # variant titles that belong to the project variant, as a list:
    variant_titles_filtered = (variants_in_db[variants_in_db['variant_abbreviation'].str.contains(project_variant)]['title']).to_list()

    # find the matching variant title from the filtered titles:
    matching_result = process.extractOne(current_project_cleaned, variant_titles_filtered, scorer = fuzz.token_set_ratio)

    if not matching_result:
        print(f'{project_variant} - Variant not in DB')
        return None
        
    matching_variant_title, matching_score = matching_result

    # get variant id for the matching variant title:
    variant_id_search = int(variants_in_db.loc[variants_in_db['title'] == matching_variant_title]['variant_id'].iloc[0])

    # for the variant id, get the sync id, sync title, and sync name
    sync_titles_filtered = syncs_in_db[syncs_in_db['variant_id'] == variant_id_search][['sync_id', 'sync_title', 'sync_name']] 

    # get sync number from the filtered sync names:
    sync_titles_filtered['sync_number_filtered'] = sync_titles_filtered['sync_name'].str.extract(sync_number_pattern) 
    
    #get sync additional name from filtered sync names:
    sync_titles_filtered['sync_add_name'] = sync_titles_filtered['sync_title'].str.extract(sync_pattern_2)

    # add current project name to all rows lol
    sync_titles_filtered['current_project'] = current_project

    # extract sync name to be searched for
    sync_titles_filtered['search_for_sync'] = sync_titles_filtered['current_project'].str.extract(sync_pattern, flags=re.IGNORECASE) 

    # extract sync number to be searched for
    sync_titles_filtered['sync_search_number'] = sync_titles_filtered['search_for_sync'].str.extract(sync_number_pattern) 

    # extract additional sync name to be searched for [for WS specifically]:
    sync_titles_filtered['project_add_search'] = sync_titles_filtered['current_project'].str.extract(sync_pattern_2)

    # flag with true or false values
    sync_titles_filtered['is_there'] = sync_titles_filtered['sync_number_filtered'] == sync_titles_filtered['sync_search_number'] 
        
    if not sync_titles_filtered['is_there'].any():
        print(current_project, ' has no matches. Check it manually')
        return None
    
    # add the true value to df
    row_to_add = sync_titles_filtered.loc[sync_titles_filtered['is_there'] == True]
    
    if len(row_to_add) > 1:
        row_to_add.reset_index(drop = True, inplace = True)
            
        for row in range(len(row_to_add)):
            if pd.notna(row_to_add.at[row, 'sync_add_name']) and pd.notna(row_to_add.at[row, 'project_add_search']):
                row_to_add.at[row, 'is_there'] = row_to_add.at[row, 'sync_add_name'] == row_to_add.at[row, 'project_add_search']

    row_to_add_final = row_to_add.loc[row_to_add['is_there'] == True][['sync_id', 'sync_title', 'current_project']]

    exhaust_df = pd.merge(left = exhaust_df, right = row_to_add_final, left_on = 'project_name', right_on = 'current_project', how = 'left')

    exhaust_df.drop(columns = ['sync_title', 'current_project'], inplace = True)

    return exhaust_df

# %%
# push to DB function
def push_exhaust_to_db(exhaust_df, exhaust_material_df, project_meshes_df, engine):
    # function takes in exhaust df, exhaust material df, project meshes df, and engine
    # pushes them to DB

    exhaust_df.to_sql('exhausts', con=engine, if_exists='append', index=False)
    exhausts_in_db = pd.read_sql("SELECT exhaust_id, project_name FROM exhausts", con=engine)
    
    exhaust_material_df = exhaust_material_df.merge(exhausts_in_db, on='project_name', how='left')
    exhaust_material_df.to_sql('exhausts_materials', con=engine, if_exists='append', index=False)
    
    meshes_df = project_meshes_df.merge(exhausts_in_db, on='project_name', how='left')
    meshes_df.to_sql('exhausts_meshes', con=engine, if_exists='append', index=False)

# %%
# extract all exhaust dfs function
def process_exhaust(thr_df, thrmd_df, flowline, variants_in_db, syncs_in_db, project_meshes_df, engine):
    # Function takes in thr, thrmd, flowline number, variants table, syncs table, meshes df, and engine connection
    # Extracts exhaust df - material df
    # Then pushes the two dfs + the meshes df imported to the push to exhaust db function

    exhaust_segments_df, exhaust_material_df = extract_exh_data(thrmd_df, thr_df, flowline)
    exhaust_df = exh_bool (exhaust_segments_df)
    exhaust_df = exhaust_2_sync(exhaust_df, thr_df, variants_in_db, syncs_in_db)

    if exhaust_df is None:
        return None

    push_exhaust_to_db(exhaust_df, exhaust_material_df, project_meshes_df, engine)

# %%
for runfolder in os.listdir(folder_path):

    project_path = os.path.join(folder_path, runfolder)

    if not os.path.isdir(project_path):                                                
        continue
    
    # Get thr and thrmd for runfolder:
    thr_df = runfolder_thr(project_path)
    thrmd_df = runfolder_thrmd(project_path)

    if isinstance (thr_df, str):
        continue

    if isinstance (thrmd_df, str):
        continue

    # Check if runfolder has flowlines:
    if not len(thrmd_df['Geometry']['FlowLines']):           
        print(runfolder, 'has no flowlines. Skipping')
        continue
   
    # Get Current project segments meshes and other data:
    project_meshes_df, flowline = extract_exh_meshes(thr_df, thrmd_df)

    if project_meshes_df is None:
        print('No exhaust flowline found. Skipping', runfolder)
        continue

    project_name = thr_df['Name']
    project_variant = project_name[:2]

    if project_variant.isdigit():
        project_name = re.sub(r'^\d+_', '', project_name)
        project_variant = project_name[:2]
        
    sync_match = re.search(sync_pattern, project_name, re.IGNORECASE) 

    if not sync_match:
        print(f'No sync pattern found in {project_name}. Skipping.')
        continue

    project_sync = sync_match.group() #sync

    # Pull Meshes Table from DB:
    exhaust_meshes_in_db = pd.read_sql("SELECT project_name, segment_name, mesh_file_name FROM exhausts_meshes", con=engine)

    # Option: Meshes table could be empty because:
    # Beginning of work - nothing in the table yet
    # In this case, the exhaust meshes are new to the DB and need to be entered
    if exhaust_meshes_in_db.empty:
        print('Exhaust Meshes DB is empty. Importing exhaust anyway.')

        result = process_exhaust(thr_df, thrmd_df, flowline, variants_in_db, syncs_in_db, project_meshes_df, engine)

        if result is None:
            continue
        
        print('Pushed new', runfolder, 'meshes to DB')
        continue
        
    exhaust_meshes_in_db['project_name_id'] = (exhaust_meshes_in_db['project_name'] != exhaust_meshes_in_db['project_name'].shift()).cumsum() - 1 #gives ids based on rows

    # Filter meshes table from DB using the current project data - same variant and sync:
    exhaust_meshes_in_db_filtered = exhaust_meshes_in_db[
    exhaust_meshes_in_db['project_name'].str.contains(project_variant, regex=False) &
    exhaust_meshes_in_db['project_name'].str.contains(project_sync, regex=False)]

    # Option: Filtered meshes table could be empty because:
    # project variant or sync are not in the table
    # In this case, the exhaust meshes are new to the DB and need to be entered
    
    if exhaust_meshes_in_db_filtered.empty:
        print('Filtered Exhaust Meshes DB is empty. Importing meshes anyway.')

        process_exhaust(thr_df, thrmd_df, flowline, variants_in_db, syncs_in_db, project_meshes_df, engine)

        if result is None:
            continue

        print('Pushed new', runfolder, 'meshes to DB')
        continue
        
    # Option 2: Meshes table not empty - do comparison
    similar_exhausts = compare_meshes(project_meshes_df, exhaust_meshes_in_db_filtered)

    if similar_exhausts:
        print('Exhaust already in DB. Moving on to next project')
    else:
        process_exhaust(thr_df, thrmd_df, flowline, variants_in_db, syncs_in_db, project_meshes_df, engine)

        if result is None:
            continue
        
        print('Pushed new', runfolder, 'meshes to DB')
        

print ('All runfolders in current directory processed.')


