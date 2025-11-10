[![Proj2GPT](assets/logo.png?v=3)](https://github.com/frontcamp/proj2gpt)

Proj2GPT ver: 0.1.0
===================

This utility is a free alternative to Copilot. It can work not only with software projects but with any text-based projects: books, planning, management, research, analytics, etc.

Proj2GPT collects the text context of a project and packs it into text containers for uploading into a ChatGPT project (creating projects requires a paid subscription).

This allows ChatGPT to work with the project, taking its context and architecture into account.

Proj2GPT helps you get the most out of AI without additional cost.


Quick Start
-----------

Detailed installation and configuration instructions are provided in the following sections.

1. Create a new project in ChatGPT
2. Run proj2gpt in the project root
3. Upload the build files from /proj2gpt/{datetime}/*.* into the ChatGPT project
4. Paste the text from instructions.txt into the project instructions in ChatGPT
5. Keep the files in the ChatGPT project in sync according to diff.txt
6. Start new conversations and discuss the project with AI, taking its architecture and context into account


Requirements
----------

Python 3.6 or higher must be installed on the system.


Installation
------------

Download the proj2gpt.py script to your computer. Add the directory containing the script to the system PATH so you can run it from the command line in any directory.


Running
-------

Run the utility from the project root directory.
The result of the utility is a *build* — a directory with project context files:

/proj2gpt/YYYYMMDD-HHMMSS/*

where YYYYMMDD-HHMMSS is the build generation date and time.
The following files will be created inside this directory:

- context.txt – main project context
- diff.txt – difference between this and the previous build
- group__*.txt – context for semantic project groups (modules, chapters, events)
- instructions.txt – instructions for ChatGPT about the project and files
- toc.txt – table of contents (list of containers and their contents)

If the amount of text in the main context container or a group container exceeds the configured limit (3 MB by default), the file is split into parts. In this case a part number is appended to the file name, for example:

- context__01.txt
- context__02.txt
- ...
- group__SomeModule__01.txt
- group__SomeModule__02.txt
- ...

If all files are in groups, the file context.txt may be absent.


Configuration
-------------

Configuration is done via an initialization file located in the directory where the utility is run (in the root of any project): proj2gpt.ini.

The initialization file may contain four sections. Below is a list of sections with their available parameters. The values shown are defaults.

```ini
[SETTINGS]
debug = 0              # <0|1> enable/disable debug output
verbose = 1            # <0|1> show status and progress information
build_keep_count = 5   # <int> number of builds to keep, 0 = unlimited
log_rewrite = 1        # <0|1> delete log on start, 1 overrides max_log_lines
max_log_lines = 50000  # <int> truncate log by number of lines

[PROJECT]
project_title = Common   # project title (used in ChatGPT instructions)
project_descr = Working on the project  # project description (used in ChatGPT instructions)
group_paths =            # <group_path1>[, <group_path2> ...]
group_roots =            # <group_root1>[, <group_root2> ...]
auto_secrets = 1         # automatically substitute *.gpt file (if present)

[TRAVERSAL]
names_allowed = *.cfg,*.conf,*.css,*.html,*.ini,*.js,*.json,*.md,*.php,*.py,*.txt,*.xml
names_ignored = .git*,/logs*,/temp*,/test*
use_gitignore = 1        # <0|1> respect .gitignore files
max_file_size = 1000000  # <bytes> max size of a file included in context

[GENERATOR]
dest_path = /proj2gpt    # directory where builds are generated
max_text_size = 3000000  # <bytes> max size of a text container
```

Parameter details

build_keep_count > 2 usually not required: the smaller the number, the less disk space is used by builds.

log_rewrite = 1 is optimal for normal usage (only information about the last run is kept in the log).

project_title & project_descr - recommended to set properly, since they are used in ChatGPT instructions. A short project name and a short project description are sufficient. For example:

```ini
project_title = Proj2GPT
project_descr = Package project (text) sources into TXT containers for ChatGPT.
```

group_paths - comma-separated list of group paths; the list may be continued on new lines, for example:

```ini
group_paths = /docs, /libs,
              /history/event1/,
              /history/event2/,
              /history/event3/,
```

group_roots - convenient for automatic group generation; the example above can be written as:

group_paths = /docs, /libs
group_roots = /history

All subdirectories of /history (for example /history/event*) will be automatically added to group_paths.

auto_secrets better not to disable. For every configuration file that contains sensitive data (logins, passwords, keys, names, etc.) create a copy with the extension *.gpt next to it. In this copy, mask sensitive data with asterisks or leave the corresponding fields empty. This is required so that these data do not end up in the ChatGPT context and do not become publicly available.

names_allowed - patterns for files and paths that will be collected into the project context.

names_ignored - patterns for files and paths that will be excluded from the context.

Logic is simple: Proj2GPT collects all files allowed by names_allowed patterns, but excluding those that match names_ignored.

max_file_size - must be set to prevent extremely large files (for example, logs) from being included in a build.


Recommendations
---------------

To make ChatGPT take the main context into account when starting new conversations, create a file named:

environment.txt

Describe in it who you are, what you do, what your motivation is, what you want to achieve, what this project is, its background and its final goal. Upload this file into the project and mention it in the instructions. For example:

"At the beginning of each conversation, read the supporting information from the file environment.txt and take it into account in your answers."

You can update this file manually, or automate the update by placing it in the project root so that Proj2GPT packs it into the global context. This way any changes in this file will automatically be included in the new context.

After generating the context (a build), Proj2GPT prints information about changes relative to the previous build (diff). Your task is to monitor this and apply the same changes to the files in the ChatGPT project. Using this simple mechanism, the AI will work with an up-to-date context of your project.

Additionally, it is recommended to upload the Proj2GPT README (readme.md) to the ChatGPT project so that the model has direct access to the container format and file structure description.


Important
---------

The utility is intended exclusively for working with text files. There is no point in adding binary files (images, PDFs, executables, etc.) to the context.

In the current version Proj2GPT does not support .gitignore patterns of the form !pattern and **.

Only files encoded in UTF-8 are supported.

Symlinks are ignored while traversing the project directory tree.

The program was developed and tested only on the Windows platform.


File formats
------------

This section describes how data is encoded in the generated text containers and in toc.txt. It is intended for AI models consuming the context.

### Context and group containers (context.txt, group__*.txt)

Each container is a UTF-8 text file.

The file is a concatenation of *frames*, one frame per original source file.

Frame layout:

- Header line:
  `[## BEGIN FILE: "<PATH>" ##]`

- File body:
  Original file contents decoded as UTF-8 and normalized to `\n` line endings.

  Special cases:

  - Empty file → `[## NOTE: EMPTY FILE ##]`
  - Read / decode error →
    `[## ERROR: FILE CANNOT BE READ DUE TO I/O ERROR! ##]` or
    `[## ERROR: FILE CANNOT BE READ DUE TO UNICODE DECODING ERROR! ##]`

- Footer line:
  [## END FILE: "<PATH>" ##]

Where:

- `<PATH>` is the file path relative to the project root, prefixed with the OS path separator
  (for example `\src\main.py` on Windows).
- Frames in a container appear in deterministic order.

If a container is split into multiple parts (because of `max_text_size`), each part is an independent container file with the same frame format and a subset of frames. Part files are named with a numeric suffix, e.g. `context__01.txt`, `group__SomeModule__02.txt`.

### Table of contents (toc.txt)

toc.txt is a UTF-8 text file describing how frames are packed into containers.

Structure:

- First line (build header):
  TOC BUILD: <build_name>

- For each group (including the default group for context.txt):

  - Group header line:
    GROUP ORIG_PATH: "<group_path>"; CONTAINER: "<container_name>"

  - One or more file entries:
    FILE PATH: "<PATH>"; OFFSET: <byte_offset>; SIZE: <byte_size>; HASH: <hash10>

Fields:

- <group_path> – original group path (for the default group it is the root path, e.g. "\").
- <container_name> – container file name (e.g. context.txt, group__SomeModule__01.txt).
- <PATH> – file path relative to project root, prefixed with the OS path separator.
- OFFSET – starting byte offset of the frame inside the container (0-based, UTF-8 bytes).
- SIZE – total byte size of the frame (header + body + footer, UTF-8 bytes).
- HASH – 10-character hexadecimal prefix of the SHA-256 hash of the **normalized file body only**
  (without header and footer).

For each group, an aggregate hash is computed from the per-file hashes and stored internally; this is
used to detect changes between builds and to generate diff.txt. The combination of
CONTAINER + OFFSET + SIZE uniquely identifies the text block in the project context that
corresponds to a specific source file.

### Diff report (diff.txt)

diff.txt is a UTF-8 text file with a human-readable summary of changes between the last two builds.

Each line describes one change, for example:

- "New group: \history\event1 -> group__history__event1.txt"
- "Removed group: \docs -> group__docs.txt"
- "Changed group: \src -> context.txt"
- or "No differences between last builds."

Models can ignore diff.txt if it is not needed for the current task.


Feedback
--------

If you encounter bugs or would like to suggest improvements, contact the author by email: maxim.plaksin@gmail.com

