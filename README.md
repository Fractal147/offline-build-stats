# offline-build-stats
Script to iterate over every commit and record some analysis - e.g. compiled code size - in git notes and local files


### Operation
The main script will run ````git log```` in the targeted repository, and working from newest to oldest commit, by hash:
- Check ````[repo-name]_analysis.json```` for an existing entry for ````[hash]```` at current version or higher
- Check ````git notes```` for an existing entry for ````[hash]```` at current version or higher
- If only one source has the info, copy it to the other one and jump to next commit, else:
- Run ````git checkout [hash]````
- Run ````[repo-name]_analysis.py````, and record the standard output
- - Store the output in the local file ````[repo-name]_analysis.json```` for the ````[hash]````
- - Store the output in git notes using  ````git notes --ref [git_notes_path] add -f -m [output]````
- Jump to next commit

When complete, or killed (CTRL-C) it will restore the repository to it's starting state.

If it crashes, it won't...


### Setup
Configure ````[repo-name]_analysis.py```` to provide the standard output (e.g. compiled flash memory usage) wanted. 
- If it's json, this will be interpreted and stored as such.
- Also configure location of git notes to write to (e.g. so it doesn't overwrite notes made in refs/notes/commits)
- Adjust version - higher version numbers will overwrite older ones in git notes and in data store.
- Place either in target location (e.g. in target repository), or in same directory as this script. This affects where the output file is stored too.


### Usage
Once set up, run ````per-commit-analysis.py [repo-directory]````, or place the file in the repo directory and run.
It is interactive only in case of error.
Output files will appear in the same directory as the ````[repo-name]_analysis.py```` script
- .json file for quick comparisons
- .csv file for output only.
- some raw.txt log files to aid parsing

### Dependencies
No deliberate ones. Developed with Python 3.8.3 on Windows, but should work with minor changes on most platforms.

### Options
- Can make it only use git notes, or only use a local file


### Future plans
- Have a more convenient output for graphing
- Use proper python module for analysis
- get git tag names with --decorate and add to output file
