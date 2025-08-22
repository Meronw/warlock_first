# Warlock_First

**Warlock_First** is a Python tool that automatically converts Windows-style paths (`\`) to Linux/Unix-style paths (`/`) inside Unreal Engine plugins and projects.  

This is especially useful when porting Unreal Engine plugins or codebases from Windows to Linux.


## Features
- Converts backslashes `\` to forward slashes `/`
- Handles `.cpp`, `.h`, `.hpp`, `.ini`, `.uplugin`, and other text-based files
- Supports `--dry-run` to preview changes without modifying files
- Supports include/exclude glob patterns
- `--aggressive` mode to catch tricky Windows paths
- Provides a summary report of changes


## Usage

Run the tool from terminal:

```bash
python3 Warlock_First.py <plugin-or-project-path> [options]


## Examples

python3 Warlock_First.py ~/Documents/UnrealProjects/MyGame/Plugins/MyPlugin --dry-run
python3 Warlock_First.py ~/Documents/UnrealProjects/MyGame/Plugins/MyPlugin --aggressive
python3 Warlock_First.py ~/Documents/UnrealProjects/MyGame/Plugins/MyPlugin --include "Source/**"


## Options

--dry-run → show changes without modifying files  
--aggressive → catch extra patterns (e.g. escaped backslashes)  
--include → only process matching files (glob patterns)  
--exclude → skip matching files/folders (glob patterns)  
--ext → specify file extensions (default: .cpp, .h, .hpp, .ini, .uplugin)


## Development

git clone https://github.com/<your-username>/warlock-first.git
cd warlock-first
python3 Warlock_First.py --help


## License

This project is licensed under the MIT License – see the [LICENSE] file for details.



