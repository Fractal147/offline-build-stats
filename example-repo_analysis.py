#Called with working directory as a git repository.
#Returns over standard output some analysis string.
#e.g. here a .json object

#CONFIGURE THE PATHS TO POINT TO THE APPROPRIATE THINGS FOR YOUR ANALYSIS BELOW:
config_dict = {
    "analysis_version" : 1, ### Higher numbers overwrite older analysis. 

    "git_notes_path":"refs/notes/analysis", #default is "refs/notes/commits" for a default repository.
        #if left blank ("") it will just use the git repository default.
    "use_git_notes": True, ##If false it ignore git notes reading and writing
    "use_local_datafile" : True, ## If false, it'll just skip all the stuff to do with saving/loading local files.
    "force_recompute_all_versions" : False ##If true, it will overwrite all past analyis (forcing  slow recompute), regardless of the version being higher
}
### Imports
import os ##for current working directory
import sys #for getting args
import subprocess ##for running the build tools and analysis
from pathlib import Path ##for nice crossplatform paths
import json #for dumping output

working_directory = Path(os.getcwd())
script_dir = Path(sys.argv[0]).parent

##ignore args unless it's "get_config" or "get_headers"
if len(sys.argv) ==2 :
    if sys.argv[1] == "get_config":
        print(json.dumps(config_dict))
        sys.exit(0) ##success
    if sys.argv[1] == "get_headers":
        ##headers used in csv printing
        print(json.dumps(["flash_Debug", "ram_Debug", "flash_Release", "ram_Release", "errors"]))
        sys.exit(0) ##success

### Check script is named correctly to work:
scriptname = Path(sys.argv[0]).name
if "_analysis.py" in scriptname:
    repo_name= scriptname.replace("_analysis.py", "")
else:
    sys.exit("Script name must include _analysis.py")

#Get name of repository it's working in:
repo_tld_return = subprocess.run(["git", "rev-parse", "--show-toplevel"], \
    capture_output=True, text=True, \
    cwd = working_directory)

if repo_tld_return.returncode != 0:
    ##Fails mainly if not a repository
    sys.exit("Does not appear to be in a git repository")

repo_tld = Path(repo_tld_return.stdout.strip('\r\n'))
repo_name_from_tld = repo_tld.name

##check repository name vs the file name:
if repo_name == repo_name_from_tld:
    pass
    #sys.exit("Good!")
else:
    sys.exit("Script must be run with working directory in the target git repo")


### Now ready to do analysis
### prep data storage:
dataout = dict()

##Built/analysis Error handling - these will be passed on on stdout
errorslist = list()

def errorout(errorstring):
    errorslist.append(errorstring)

##configure paths for working with
repo_dir = repo_tld


#Predelete compiled files (A clean build would be acceptable too instead)
path_to_Debug_elf = repo_dir.joinpath(Path(r"\Debug\microdriver-dev-start.elf"))
path_to_Debug_elf.unlink(missing_ok=True) ##actually delete

path_to_Release_elf = repo_dir.joinpath(Path(r"\Release\microdriver-dev-start.elf"))
path_to_Release_elf.unlink(missing_ok=True) ##actually delete


##Build this commit
path_to_atmel_studio = Path(r"C:\Program Files (x86)\Atmel\Studio\7.0\AtmelStudio.exe")
path_to_atlsn = repo_dir.joinpath(Path(r"example.atsln")) 

try:
    subprocess.run([ path_to_atmel_studio, path_to_atlsn, r"/build",  "Debug" ] ,timeout=30, check=True) ##timeout in seconds
    pass
except subprocess.CalledProcessError:
    errorout("Build_Debug_Failed")
    pass
except subprocess.TimeoutExpired:
    errorout("Build_Debug_Timeout")
    pass


try:
    subprocess.run([ path_to_atmel_studio, path_to_atlsn, r"/build",  "Release" ] ,timeout=30, check=True) ##timeout in seconds
    pass
except subprocess.CalledProcessError:
    errorout("Build_Release_Failed")
    pass
except subprocess.TimeoutExpired:
    errorout("Build_Release_Timeout")
    pass



#Extract information:

path_to_analysis_tool = Path(r"C:\Program Files (x86)\Atmel\Studio\7.0\toolchain\avr8\avr8-gnu-toolchain\bin\avr-objdump.exe")
#path_to_analysis_tool =Path(r"C:\Program Files (x86)\Atmel\Studio\7.0\toolchain\avr8\avr8-gnu-toolchain\bin\avr-size.exe")

try:
    #size_txt = subprocess.run([path_to_analysis_too, path_to_elf ], capture_output=True, text=True, timeout=5, check=True ).stdout ##timeout in seconds
    analysis_Debug_txt = subprocess.run([path_to_analysis_tool, "-Pmem-usage", path_to_Debug_elf ], \
        capture_output=True, text=True, timeout=5, check=True ).stdout ##timeout in seconds 

    dataout['flash_Debug'] = int(analysis_Debug_txt.splitlines()[6].split(":")[1].split("b")[0].strip())
    dataout['ram_Debug'] = int(analysis_Debug_txt.splitlines()[9].split(":")[1].split("b")[0].strip())
except subprocess.CalledProcessError:
    errorout("Analysis_Debug_Failed")
    pass
except subprocess.TimeoutExpired:
    errorout("Analysis_Debug_Timeout")
    pass

try:
    analysis_Release_txt = subprocess.run([path_to_analysis_tool, "-Pmem-usage", path_to_Release_elf ], \
        capture_output=True, text=True, timeout=5, check=True ).stdout ##timeout in seconds 
    dataout['flash_Release'] = int(analysis_Release_txt.splitlines()[6].split(":")[1].split("b")[0].strip())
    dataout['ram_Release'] = int(analysis_Release_txt.splitlines()[9].split(":")[1].split("b")[0].strip())
except subprocess.CalledProcessError:
    errorout("Analysis_Release_Failed")
    pass
except subprocess.TimeoutExpired:
    errorout("Analysis_Release_Timeout")
    pass

##Format size form avr-size
#   text    data     bss     dec     hex filename
#   8083      27      65    8175    1fef c:\Users\name\Documents\Git working copies\example-repo\Debug\microdriver-dev-start.elf

## or using avr-objdump:
# 0
# 1 c:\Users\name\Documents\Git working copies\example-repo\Debug\microdriver-dev-start.elf:     file format elf32-avr
# 2 AVR Memory Usage
# 3 ----------------
# 4 Device: attiny816
# 5
# 6 Program:    7510 bytes (91.7% Full)
# 7 (.text + .data + .bootloader)
# 8
# 9 Data:         83 bytes (16.2% Full)
# 10 (.data + .bss + .noinit)
# 11
# 12

##Add the errors key if there were any
if len(errorslist) > 0:
    dataout['errors'] = errorslist

##dataout['analysis_version'] = config_dict["analysis_version"]

#Oass on as standard output
outstring =json.dumps(dataout) 
print(outstring)

exit(0) #success!