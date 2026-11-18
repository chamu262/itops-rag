# loaders

One loader per source type (Markdown, PDF, Confluence HTML export, Jira CSV / ServiceNow JSON tickets, YAML change records). Each returns `Document` objects with access tags. `load_path` walks a folder and never stops on one bad file.
