#####CONFIGURATION#####
#all now in _analysis.py script



import sys #for getting args
from pathlib import Path #For doing nice crossplatform paths
import subprocess ##for running more command line stuff
import json #for config and analysis store

##### Working out what the target repository is and working directory for this script
script_calling_directory =Path(Path(sys.argv[0]).parent.resolve())

if len(sys.argv) > 1:
    ##Argument given, accept it as path to repository.
    target_repo_directory = Path(Path(sys.argv[1]).resolve())
else:
    #No arguments given, use current script path as target
    target_repo_directory = script_calling_directory


##### Checking to see if it's a valid repository
repo_validity = subprocess.run(["git", "rev-parse", "--show-toplevel"], \
    capture_output=True, text=True, \
    cwd = target_repo_directory)

if repo_validity.returncode != 0:
    ##Usually not a repository
    sys.exit(repo_validity.stderr)

repo_name = Path(repo_validity.stdout.strip('\r\n')).name


### Store as place to seek:
target_repo_toplevel_directory = Path(Path(repo_validity.stdout.strip('\n\r')).resolve())
if not target_repo_directory == target_repo_toplevel_directory:
    print("Not pointing at toplevel directory of repository, carrying on")
    ##could exit here, too.
    pass

##List (in order) of places to look for files, and to write database
directories_to_seek = [\
    target_repo_directory, 
    script_calling_directory,
    target_repo_toplevel_directory
    ]



##Seek out the analysis file, then store the location (for putting data into)
for directory in directories_to_seek:
    analysis_script_path = directory.joinpath(repo_name + "_analysis.py")
    if analysis_script_path.exists():
        break

if not analysis_script_path.exists():
    sys.exit("Could not find analysis script: " + analysis_script_path.name)

working_directory = analysis_script_path.absolute().parent

print("Using analysis file " + analysis_script_path.as_posix())



## Get configuration from analysis file:
config_json = subprocess.run(["python", analysis_script_path, "get_config"], \
    text=True, capture_output=True, check=True).stdout.strip('\r\n')

print("Config:\t", config_json)
config_dict = json.loads(config_json)

####validate config
expected_keys = [
    "analysis_version" ,
    "git_notes_path",
    "use_git_notes",
    "use_local_datafile",
    "force_recompute_all_versions"
]
for key in expected_keys:
    try:
        assert key in config_dict
    except AssertionError: 
        sys.exit("Error - config in _analysis.py missing parameter, " + key)
        
        




### Now seek out the database file, try to load it, and otherwise setup a blank one
outfile_json_path = working_directory.joinpath(repo_name + "_analysis_output.json")

if config_dict['use_local_datafile'] and outfile_json_path.exists():
    try:
        with open(outfile_json_path) as db_file:
            analysis_data= json.load(db_file)
    except json.decoder.JSONDecodeError:
        print("JSON error!")
        if input("DELETE to start from fresh, else exit\t") == "DELETE":
            analysis_data = dict()
        else:
            exit()
else:
    analysis_data= dict()
    
if not 'commits' in analysis_data:
    analysis_data['commits'] = dict()

if config_dict['use_local_datafile']:
    print("Using local data file file " + outfile_json_path.as_posix())



### Use git to find repository location at beginning to return to./

location_at_start = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], \
    cwd=target_repo_directory, capture_output=True, text=True).stdout
location_at_start = location_at_start.strip(' \n\t\r')

if location_at_start == "HEAD":
    print("Starting in detached head mode", flush=True)
    location_at_start = subprocess.run(["git", "rev-parse", "HEAD"], \
        cwd=target_repo_directory, capture_output=True, text=True).stdout
    location_at_start = location_at_start.strip(' \n\t\r')

else:
    print("Starting at top of branch \t" +location_at_start, flush=True)




##handler to detect ctrl-c break
# Todo: expand to other crashes?
import signal
import sys
def signal_handler(sig, frame):
    print('Aborting!', flush=True)
    ##write out the database
    if config_dict['use_local_datafile']:
        with open(outfile_json_path , 'w') as outfile:
            print("Writing out to file", flush=True)
            json.dump(analysis_data, outfile, indent=2)
    
    print("Restoring HEAD location", flush=True)
    subprocess.run(["git", "checkout", location_at_start], cwd=target_repo_directory)

    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)







##Get a list of all commits, formatted as JSON
#Output to file since it may be huge (and buffer for subprocess is not)
raw_git_log_path = working_directory.joinpath(repo_name+ "_raw_git_log.txt")
subprocess.run([ "git",  "log", "--output="+str(raw_git_log_path), \
    #'''--pretty=format:%n  "%H":{%n  "author": "%aN <%aE>",%n  "date": "%ad",%n  "message": "%f",%n  "notes": "%N"%n},''' \ ##unused since notes now separate
    '''--pretty=format:%n  "%H":{%n  "author": "%aN <%aE>",%n  "date": "%ad",%n  "message": "%f"%n},''' \
    ] ,capture_output=True, text=True, \
    timeout=5, check=True, cwd=target_repo_directory ) ##timeout in seconds


with open(raw_git_log_path, 'tr') as raw_git_log:
    ##raw_git_log_mmap = mmap.mmap(raw_git_log.fileno(), 0)
    ##re.sub("commit","", raw_git_log_mmap)

    raw_git_log_list_of_lines =raw_git_log.readlines()

##Make it more valid JSON:
raw_git_log_list_of_lines.insert(0,'{"commitlist":{\n')
raw_git_log_list_of_lines[-1] = '}}}'

with open(raw_git_log_path, 'tw') as raw_git_log:
    raw_git_log.writelines(raw_git_log_list_of_lines)

##parse the git log
with open(raw_git_log_path) as raw_git_log:
        commit_list= json.load(raw_git_log)['commitlist']




#Overal plan is then :
#Read the database for valid/not-> valid_results, mark.
#read git log for valid/not-> valid_results, mark
#Don't worry about mismatches at this stage.

#if neither valid, run script-> valid_results

#if database invalid, overwrite.
#if log invalid, overwrite.

#can skip local file stuff.

##Using the git log as the master copy, so it goes in order from new to old:


#Prepare dicts for holding notes (blank is fine if unused)
analysis_from_notes = dict()
analysis_from_notes['commits'] = dict()

#get list of notes in a simiar manner to the plain git log
#Output to file since it may be huge (and buffer for subprocess is not)
##note that may contain various nasties, so delimit with care.
if config_dict["use_git_notes"]:
    #Get a list of all commits, in a file, separated
    raw_git_notes_path = working_directory.joinpath(repo_name+ "_raw_git_notes.txt")
    if config_dict['git_notes_path'] == "":
        get_notes_command = ["git", "log", "--output="+str(raw_git_notes_path), \
            "--notes", '''--format=%H{NOTE_DELIM}%N{END_OF_NOTE}''']
    else:
        get_notes_command = ["git", "log", "--output="+str(raw_git_notes_path),\
            "--notes="+config_dict['git_notes_path'],'''--format=%H{NOTE_DELIM}%N{END_OF_NOTE}''' ]

    subprocess.run( get_notes_command ,capture_output=True, text=True, \
        timeout=5, check=True, cwd=target_repo_directory ) ##timeout in seconds

    #In file delete all newlines, except for {END_OF_NOTE}
    with open(raw_git_notes_path, 'tr') as raw_git_notes:
        git_notes_all = raw_git_notes.read()
        git_notes_all = git_notes_all.replace('\n', '')
        git_notes_all = git_notes_all.replace('\r', '')
        git_notes_all = git_notes_all.replace('{END_OF_NOTE}', '{NOTE_DELIM}\n')
    
    with open(raw_git_notes_path, 'tw') as raw_git_notes:
        raw_git_notes.write(git_notes_all)

    
    #Read file line by line, split by the delimiter
    #If there is a string,  and add to appropriate database 
    with open(raw_git_notes_path, 'tr') as  clean_git_notes:
        for line in clean_git_notes:
            ##each line one note.
            linesplit= line.split("{NOTE_DELIM}")

            if len(linesplit) != 3:
                continue ##skip if it's somehow got more delimiters
            if len(linesplit[1]) < 1:
                continue ##skip if it has no text
            #print(linesplit)
            #Try and load it as a JSON string, otherwise add as analysis_str

            try:
                analysis_from_notes['commits'][linesplit[0]] = json.loads(linesplit[1])
                
            except json.decoder.JSONDecodeError:
                analysis_from_notes['commits'][linesplit[0]] = {'analysis_str':linesplit[1]}
                



##For commits

limiter = 0
for commit in commit_list:
    limiter = limiter +1
    if limiter > 3:
        #break ##debug thing to enable writing it to not go mad
        pass

    #setup validity flags:
    db_analysis_valid = False
    notes_analysis_valid = False
    print_a_line = False
    valid_data = dict()

    #check local datafile for valid data by checking version (if unused, analysis_data is blank)
    if commit in analysis_data['commits']:
        #print("Found", flush=True, end='\t')
        if analysis_data['commits'][commit].get('analysis_version', -1) >= config_dict['analysis_version']:
            db_analysis_valid = True
            valid_data = analysis_data['commits'][commit]
            valid_data.pop('message',"Don't need messages in the git notes")

    #check notes list for valid data by checking version  (if unused, analysis_from_notes is blank)
    if commit in analysis_from_notes['commits']:
        if analysis_from_notes['commits'][commit].get('analysis_version', -1) >= config_dict['analysis_version']:
            notes_analysis_valid = True
            valid_data = analysis_from_notes['commits'][commit]
    

    if config_dict.get("force_recompute_all_versions", False) or \
        (not (db_analysis_valid) and config_dict['use_local_datafile'] )or \
        (not (notes_analysis_valid) and config_dict['use_git_notes']):
        print_a_line = True
        print(commit, end=' ', flush=True)

    
    #Recompute if neither valid, or recompute is set
    if config_dict.get("force_recompute_all_versions", False) or \
        ( not (db_analysis_valid or notes_analysis_valid)):

        ##generate the analysis data
        print("Testing.", end='', flush=True)
        subprocess.run(["git", "checkout", commit], cwd=target_repo_directory, capture_output=True)
        print(".", end='', flush=True)
        analysis_str = subprocess.run(["python", analysis_script_path], \
            cwd=working_directory, capture_output=True, text=True, check=True).stdout
        print(".\t", end='', flush=True)
        analysis_str=analysis_str.strip('\n\r')

        #if analysis_str is valid json, treat it as such in the data store
        try:
            analysis_dict_onecommit = json.loads(analysis_str)
            valid_data['analysis'] = analysis_dict_onecommit
        except json.decoder.JSONDecodeError:
            valid_data['analysis_str'] = analysis_str
        
        valid_data['analysis_version'] = config_dict['analysis_version']

        print(json.dumps(valid_data), flush=True, end='\t')
        

    valid_data_string =json.dumps(valid_data) 

    ## update local data store (only written out if enabled)
    if config_dict["use_local_datafile"] and \
        (config_dict.get("force_recompute_all_versions", False) or not (db_analysis_valid)):
        print("Updating dict", flush=True, end='\t')
        analysis_data['commits'][commit] = valid_data
        analysis_data['commits'][commit]['message'] = commit_list[commit]['message']
        #print("Updated", flush=True, end='\t')


    ## update git notes if needed
    if config_dict["use_git_notes"] and \
        (config_dict.get("force_recompute_all_versions", False) or not (notes_analysis_valid)):
        
        print("Updating git notes", flush=True, end='\t')
        if config_dict['git_notes_path'] == "":
            notes_add_command = ["git", "notes", "add", "-f","-m", valid_data_string, commit]
        else:
            notes_add_command = ["git", "notes", "--ref="+config_dict['git_notes_path'], "add", "-f","-m", valid_data_string, commit]
        #write to git database as string
        subprocess.run(notes_add_command, \
            check=True, cwd=target_repo_directory, capture_output=True)

    if print_a_line:
        print("", flush=True) ##use for a newline

    ##complete, next commit
        


##for all commits in data.commits[:], run the analysis script
#store the results under the commit object in the data?







#for each commit, it will checkout that commit, compile, and report sizes.
#then add them to the .csv.
#If already existant in the csv, it will NOT show.

#it COULD...add to git notes. too...


#The actual script to run is in the repo, under [reponame]_fw-size.py



##Output


#Hmm. So it would be helpful for it to list all data in a csv or somesuch
#or a database!
#Python dict for now for each commit
#so a list of dicts
#If needs be, list is ordered in order of git log.
#With most recent on top...

#no versions or anything.



#end
print("Completed, up to date")
##see more here https://stackoverflow.com/questions/12309269/how-do-i-write-json-data-to-a-file
if config_dict['use_local_datafile']:
    with open(outfile_json_path , 'w') as outfile:
        print("Writing out to file", flush=True)
        json.dump(analysis_data, outfile, indent=2)
        

print("Restoring HEAD location", flush=True)
subprocess.run(["git", "checkout", location_at_start], cwd=target_repo_directory)


#Pretty printing to .csv file
print("Pretty printing to .CSV file", flush=True)
outfile_csv_path = working_directory.joinpath(repo_name + "_analysis_output.csv")
out_csv_list = []

## Get headers from analysis file:
headers_json = subprocess.run(["python", analysis_script_path, "get_headers"], \
    text=True, capture_output=True, check=True).stdout.strip('\r\n')

#print("Config:\t", config_json)
headers_list = json.loads(headers_json)

header_line = "num,commit,date,message,analysis_version,analysis_str"
for item in headers_list:
    header_line = header_line +',' +item
out_csv_list.append(header_line + '\n')

# import csv
# with open(outfile_csv_path, 'tw') as outfile_csv:
#     writer1= csv.DictWriter(outfile_csv, fieldnames= )


linenum = 0
for commit in commit_list:
    linenum= linenum+1
    out_line = ""
    out_line = out_line + str(linenum) + ","
    out_line = out_line + commit + ","
    out_line = out_line + commit_list[commit]['date'] + ","
    out_line = out_line + commit_list[commit]['message'] + ","
    if commit in analysis_data['commits']:
        out_line = out_line + str(analysis_data['commits'][commit].get("analysis_version","")) + ","
        out_line = out_line + str(analysis_data['commits'][commit].get("analysis_str","")).replace(',',';')
        if "analysis" in analysis_data['commits'][commit]:
            for param in headers_list:
                out_line = out_line +","+ str(analysis_data['commits'][commit]["analysis"].get(param,"")).replace(',',';') 

    out_csv_list.append(out_line + '\n')

with open(outfile_csv_path, 'tw') as outfile_csv:
    outfile_csv.writelines(out_csv_list)

exit()