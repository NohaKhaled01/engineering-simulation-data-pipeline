# %%
import pandas as pd
import json as js
import os
import re

# %%
folder_path = os.getcwd()

# %% Pattern to identify gas data tables — update to match your simulation software naming convention
gas_data_pattern = re.compile(r'GasData_?T?a?b?l?e?s?')
df = pd.DataFrame()
project_names = []

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
# Final trial, function version -- getting parameter names for parameters type 11:

def parameters_11_names(thrmd_df):

    parameters_dict = {}

    number_of_parameters = len(thrmd_df['Parameters'])

    for parameter in range(number_of_parameters):
        parameter_type = thrmd_df['Parameters'][parameter]['Type']

        if parameter_type == 11:
            parameter_name = thrmd_df['Parameters'][parameter]['Name']
            parameter_id = thrmd_df['Parameters'][parameter]['Id']

            parameters_dict[parameter_name] = parameter_id

    return parameters_dict


# %%
# Final trial, function version -- create a dict for the thermal table names and IDs:

def thermal_project_tables(thrmd_df):
    table_dict = {}
    number_of_tables = len(thrmd_df['ThermalTables'])
    
    for table in range(number_of_tables):
        thermal_table_name = thrmd_df['ThermalTables'][table]['Name']
        thermal_table_id = thrmd_df['ThermalTables'][table]['TableDataParameter']['Value']

        table_dict[thermal_table_name] = thermal_table_id

    return table_dict

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

    parameters_11_dict = {}
    parameters_11_dict = parameters_11_names(thrmd_df)
    
    thermal_tables = {}
    thermal_tables = thermal_project_tables(thrmd_df)

    thermal_tables_names = list(thermal_tables.keys())

    for name in thermal_tables_names:
        result = gas_data_pattern.search(name)
        if result:
            table_name = result.group()
            gas_data_id = thermal_tables[table_name]
            break
    
    if not result:
        continue

    for parameter in range(len(thrmd_df['Parameters'])):
        parameter_id = thrmd_df['Parameters'][parameter]['Id']
        if parameter_id == gas_data_id:
            parameter_num = parameter

    #One final check:
    if thrmd_df['Parameters'][parameter_num]['Type'] != 11:
        print('Wrong Parameter Type Chosen -- Continuining')
        continue

    print(runfolder)
    project_names.append(thr_df['Name'])
    
    # Getting cases indices and names in a dict:
    cases_dict = {}
    number_of_cases = len(thrmd_df['Cases'])
    
    for case in range(number_of_cases):
        cases_dict[case] = thrmd_df['Cases'][case]['Name']

    # Extract the names of the columns of one table:
    # All tables will have the same column names, and column units, so need to do this only once.

    table_columns_dict = {}
    
    table_num = 0

    table = thrmd_df['Parameters'][parameter_num]['CasesValues'] #saving path

    table_columns = table[table_num]['TableData']['Columns'] #saving path -- access the columns inside the table 

    case_name = cases_dict[table_num]

    number_of_columns = len(table_columns)

    for column in range(number_of_columns):
        # column = 0 .. 
        column_name = table_columns[column]['Name']
        column_unit = table_columns[column]['Unit']['Name']
        #table_columns_dict[column_name].add(column_unit)
        table_columns_dict[column_name] = column_unit
        
    row_to_add = pd.DataFrame([table_columns_dict.keys(), table_columns_dict.values()])
    df = pd.concat([df, row_to_add], ignore_index=True)
    
print('Done Runfolders in Current Directory.')

# %%
row = df.index.size
start_row = 0
column = df.columns.size
for project in project_names:
    df.loc[start_row, column] = project
    start_row += 2

# %%
save_to_directory = os.path.join(os.getcwd(), 'Columns')
if not os.path.exists(save_to_directory):
    os.mkdir(save_to_directory) 
save_to_path = os.path.join(os.getcwd(), 'Columns', 'Column_Names.csv')
df.to_csv(save_to_path)


