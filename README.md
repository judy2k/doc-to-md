# Doc-to-Markdown

This is a small command-line utility for converting Google Docs documents to
Markdown that's suitable for pasting into ContentStack.

## What does it actually do?

- Firstly, the script will identify any code blocks (formatted using Fira Code, Roboto Mono, Source Code Pro, or Courier New) and will mark them as code blocks in the resulting Markdown.
- Some basic heuristics are used to annotate code blocks as python code
- Inline code can be correctly identified using backticks (the same as Markdown itself) or formatting (any spans marked with a code font).
- Empty paragraphs are removed
- Hyperlinks are correctly extracted from Google's nasty tracking links.
- Bold and italic formatting is maintained where possible.

## Installation

```
brew install pandoc    # <- MacOS or Linuxbrew
# apt install pandoc   # <- Debian/Ubuntu
# choco install pandoc # <- Windows with Chocolatey
# ... or see here for more instructions: https://pandoc.org/installing.html

python -m pip install --upgrade git+https://github.com/judy2k/doc-to-md.git

# Check that it worked:
doc2md --help
```

## Usage

The tool doesn't have many options, so using it is relatively straightforward.

First, download your Google Doc as a Web Page.

![A screenshot of the Export as Web Page menu item in Google Docs.](images/export_screenshot.png)

Unzip the archive, and then in the command-line, run something like the following:

```
# Create a new Markdown file from an existing Google Docs HTML file:
doc2md /PATH/TO/INPUT.HTML /PATH/TO/OUTPUT.MD
```

This should produce a clean, formatted Markdown file, suitable for copying into ContentStack.
You will, sadly, still have to import all your images and insert them in the correct locations yourself.

## To-Do

- ContentStack doesn't support `--` and `---` so replace them (outside of code blocks!) with n-dash and m-dash characters.
- Resulting Markdown occasionally includes backslash followed by line-break characters. Need to identify why it's happening and fix.
- Is there a way to manage images better?
- Can captions in the doc automatically be applied to the associated image?
