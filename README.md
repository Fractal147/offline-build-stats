# offline-build-stats
Script to iterate over every commit and record some analysis - e.g. compiled code size - in git notes and a local file.


### Operation
The main script will run ````git log```` in the targeted repository, and working from newest to oldest commit, by hash:
- Check ````[repo-name]_analysis.json```` for an existing entry for ````[hash]````
- - If present, skip to next commit
- - If not present, proceed:
- Run ````git checkout [hash]````
- Run ````[repo-name]_analysis.py````, and record the standard output
- - Store the output in the local file ````[repo-name]_analysis.json```` for the ````[hash]````
- - Store the output in git notes using  ````git notes --ref [git_notes_path] add -f -m [output]````
- Jump to next commit

When complete, or killed (CTRL-C) it will restore the repository to it's starting state.


### Setup
Configure ````[repo-name]_analysis.py```` to provide the standard output (e.g. compiled flash memory usage) wanted. Place either in target repository, or in same directory as this script.
Configure ````per-commit-analysis.py```` to point at the appropriate notes directory (e.g. so it doesn't overwrite notes made in refs/notes/commits)


### Usage
Once set up, run ````per-commit-analysis.py [repo-directory]````, or place the file in the repo directory and run.
It is interactive only in case of error.


### Dependencies
No deliberate ones. Developed with Python 3.8.3 on Windows, but should work with minor changes on most platforms.


### Future plans
- Have it optionally read git notes only - no local database
- Have it do some form of versioning/validation of stored data
- Have a more convenient output for graphing
- Have the ````_analysis.py```` file contain the notes parameters, and import
