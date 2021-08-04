#####CONFIGURATION#####
git_notes_path = "refs/notes/analysis1" #default is "refs/notes/commits" for a default repository.



import sys #for getting args
from pathlib import Path #For doing nice crossplatform paths
import subprocess ##for running more command line stuff


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

### Now seek out the database file, try to load it, and otherwise setup
import json
outfile_json_path = working_directory.joinpath(repo_name + "_analysis_output.json")

if outfile_json_path.exists():
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
    with open(outfile_json_path , 'w') as outfile:
        json.dump(analysis_data, outfile, indent=2)
    
    print("Restoring HEAD location", flush=True)
    subprocess.run(["git", "checkout", location_at_start], cwd=target_repo_directory)

    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)







##Get a list of all commits, formatted as JSON
raw_git_log_path = working_directory.joinpath(repo_name+ "_raw_git_log.txt")
subprocess.run([ "git",  "log", "--output="+str(raw_git_log_path), \
    #'''--pretty=format:%n  "%H":{%n  "author": "%aN <%aE>",%n  "date": "%ad",%n  "message": "%f",%n  "notes": "%N"%n},''' \ ##unused since notes now separate
    '''--pretty=format:%n  "%H":{%n  "author": "%aN <%aE>",%n  "date": "%ad",%n  "message": "%f"%n},''' \
    ] ,capture_output=True, text=True, \
    timeout=5, check=False, cwd=target_repo_directory ) ##timeout in seconds


with open(raw_git_log_path, 'tr') as raw_git_log:
    ##raw_git_log_mmap = mmap.mmap(raw_git_log.fileno(), 0)
    ##re.sub("commit","", raw_git_log_mmap)
   
    raw_git_log_list_of_lines =raw_git_log.readlines()

##Make it more valid JSON
raw_git_log_list_of_lines.insert(0,'{"commitlist":{\n')
raw_git_log_list_of_lines[-1] = '}}}'

with open(raw_git_log_path, 'tw') as raw_git_log:
    raw_git_log.writelines(raw_git_log_list_of_lines)

####Old methods for fixing file when it had notes in...
# ##Time efficient, space poor:
# raw_git_log_list_of_lines_fixed = list()
# raw_git_log_list_of_lines_fixed.append('{"commitlist":{\n')
# # for line in raw_git_log_list_of_lines:
# #     if re.match('^"$', line):
# #         #skip this line, and fix the previous
# #         raw_git_log_list_of_lines_fixed[-1] = raw_git_log_list_of_lines_fixed[-1][:-1] +'"' +raw_git_log_list_of_lines_fixed[-1][-1]
# #     else:
# #         raw_git_log_list_of_lines_fixed.append(line)
# #         ##add this line to the list
# ##fix the last line
# raw_git_log_list_of_lines_fixed[-1] = '}}}'
# with open(raw_git_log_path, 'tw') as raw_git_log:
#     raw_git_log.writelines(raw_git_log_list_of_lines_fixed)

    

##parse the git log
with open(raw_git_log_path) as raw_git_log:
        commit_list= json.load(raw_git_log)['commitlist']

##removed since it was never going to work
##if the notes look like json...?
# for commit in commit_list:
#     if not commit_list[commit].get('notes',"") == "":
#         try:
#             analysis = json.loads(commit_list[commit]['notes'])
#             commit_list[commit]['analysis'] = analysis
#         except json.decoder.JSONDecodeError:
#             print("Fail decode\t" + commit_list[commit]['notes'])
#             pass





#print(plain_git_log)
#for commit_a in commit_list:
    #print(commit_list[commit_a].get("author"))
    


##Using the git log as the master copy...
limiter =0
for commit in commit_list:
    
    if commit in analysis_data['commits']:
        #data already present
        print(commit+"\tData present:\t"+str(analysis_data['commits'][commit]), flush=True)
        
        pass
    else:
        #todo: check git notes for data:
        #potentially ask if it should overwrite?

        ##generate the test data
        print(commit+"\tTesting.", end='', flush=True)
        subprocess.run(["git", "checkout", commit], cwd=target_repo_directory, capture_output=True)
        print(".", end='', flush=True)
        analysis_str = subprocess.run(["python", analysis_script_path], \
            cwd=working_directory, capture_output=True, text=True, check=True).stdout
        print(".\t", end='', flush=True)
        analysis_str=analysis_str.strip('\n\r')

        #if analysis is valid json, treat it as such in the data store
        try:
            analysis_commit_dict =dict()
            analysis_commit_dict = json.loads(analysis_str)
            analysis_good_json = True
            pass
        except json.decoder.JSONDecodeError:
            analysis_good_json = False
            pass

        print(analysis_str, flush=True)
        ##add to dict.
        analysis_data['commits'][commit] = dict()
        analysis_data['commits'][commit]['message'] = commit_list[commit]['message']
        if analysis_good_json:
            analysis_data['commits'][commit]['analysis'] = analysis_commit_dict
        else:
            ##write it like text
            analysis_data['commits'][commit] = dict()
            analysis_data['commits'][commit]['analysis_str'] = analysis_str
        

        #write to git database as string
        subprocess.run(["git", "notes", "--ref", git_notes_path, "add", "-f","-m", analysis_str], check=True, cwd=target_repo_directory, capture_output=False)
        
        


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
##see more here https://stackoverflow.com/questions/12309269/how-do-i-write-json-data-to-a-file
with open(outfile_json_path , 'w') as outfile:
    json.dump(analysis_data, outfile, indent=2)

print("Restoring HEAD location", flush=True)
subprocess.run(["git", "checkout", location_at_start], cwd=target_repo_directory)
exit()