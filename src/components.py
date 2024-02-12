from pathlib import Path
from typing import Optional

from symai import Symbol, Function
from symai.extended import BibTexParser
from symai.components import Sequence, Parallel, FileReader
from symai.extended import Conversation
from symai.post_processors import StripPostProcessor, CodeExtractPostProcessor


DEFAULT_BIB_PATH = (Path(__file__).parent.absolute() / "documents" / "bib" / "references.bib").as_posix()

GLOBAL_PAPER_CONTEXT = """Write a scientific paper about the machine learning framework called SymbolicAI which operates on the following principles:
- Symbolic methods
- Sub-symbolic methods
- Neural-symbolic methods
- Probabilistic programming methods
- Cognitive architectures
Be precise in your writing and follow a scientific style. Do not use any colloquial language. However, formulate simple and understandable sentences.
Avoid using filler word and phrases. Be highly technical and precise in your writing style."""


PAPER_STATIC_CONTEXT = """[General Context]
{context}

[Detailed Description]
Your output format should be parsable by a LaTeX compiler. All produced content should be enclosed between the \n```latex\n ... \n``` blocks. Do not create document classes or other LaTeX meta commands. Always assume that the document class is already defined. Only produce exactly one latex block with all your content.
Only use either `section`, `subsection`, paragraph`, `texttt`, `textbf`, `emph` or `citep` commands to structure your content. Do not use any other LaTeX commands.
NEVER change the citation style / tag names. Always keep the original `cite` or `citep` format, i.e. `\citep{{Placeholder:YY}}` remains as is at the same position in your text, where `Placeholder` represents the actual citation name and `YY` the two digit year format. Here are some examples: `\citep{{Newell:56}}`, `\citep{{Newell:57}}`, `\citep{{Laird:87}}`, `\citep{{Newell:72}}`, `\citep{{McCarthy:06}}`.

The following is a general example of your expected output:

[Example]
```latex
\\documentclass{{article}}
\\begin{{document}}
% TODO: your content here
\\end{{document}}
```
Do not create `\\begin{{document}}` or `\\end{{document}}` commands. Only the content that would be placed into the TODO block expected between ```latex ... ``` if not otherwise specified.
NEVER repeat a section or subsection name if one already exists in the document.

{description}
"""


DO_NOT_CHANGE_CITATIONS = "Do NOT ADD ANY NEW citations or references. Just focus on the content / summary and preserve 1:1 existing citations and references if there are any."


class Paper(Function):
    def __init__(self, *sequence, context: str = GLOBAL_PAPER_CONTEXT, **kwargs):
        super().__init__(**kwargs)
        self.sequence = Sequence(*sequence)
        self.context  = context

    def forward(self, task, **kwargs):
        # execute the sequence of tasks
        res         = self.sequence(task, **kwargs)
        # access results from the global root node metadata
        results     = self.linker.results
        # all other results except the title, abstract, cite and source:
        document    = [results[key].__str__() for key in results if not any([task in key for task in ['Title', 'Abstract', 'Cite', 'Source', 'Parallel', 'Sequence']]) and results[key].value_type == str]
        # reverse the order of the document to match the expected output
        document    = document[::-1]
        # create the final result
        result = Symbol({
            "title": self.linker.find('Title').__str__(),
            "abstract": self.linker.find('Abstract').__str__(),
            "document": "\n".join(document)
        })
        return result


    @property
    def static_context(self):
        return PAPER_STATIC_CONTEXT.format(context=self.context,
                                           description=f'''The final paper must include the title an abstract and a related work section and method section.
Try to preserve the original content and generate a coherent text based on the provided context.

[Format]
Instead of the ```latex ... ``` format, print the output in a ```json ... ``` format as shown below with the following structure:
```json
{{
  "title": "Your title...",
  "abstract": "Your abstract...",
  "document": "Your other sections, subsections, and paragraphs and all the content e.g. introduction, related work, method, etc. ..."
}}
```
Include all the LaTeX commands and content in the `document` field. Preserve ALL the original citations, references  and content according to best scientific writing practices.
The final document should be at least 2 pages long.
{DO_NOT_CHANGE_CITATIONS}
''')


class Context(Conversation):
    def __init__(self, context: str = GLOBAL_PAPER_CONTEXT, **kwargs):
        super().__init__(**kwargs)
        self.auto_print   = False
        self.prompt       = 'Replace the % TODO: with your content and follow the task description below.'
        self.context      = context

    def forward(self, task, *args, **kwargs):
        function = Function(self.prompt,
                            post_processors=[StripPostProcessor(), CodeExtractPostProcessor()],
                            static_context=self.static_context,
                            dynamic_context=self.dynamic_context)
        return function(task, *args, **kwargs)

    @property
    def description(self):
        raise NotImplementedError()

    @property
    def static_context(self):
        return PAPER_STATIC_CONTEXT.format(context=self.context, description=self.description)


class Source(Context):
    bib_parser = BibTexParser()
    reader     = FileReader()
    bib_references = [line for line in reader(DEFAULT_BIB_PATH) / '\n\n' if line]

    def __init__(self,
                 context: str = GLOBAL_PAPER_CONTEXT,
                 bib_link: Optional[str] = None,
                 file_link: Optional[str] = None,
                 url_link: Optional[str] = None,
                 bib_path: str = DEFAULT_BIB_PATH,
                 **kwargs):
        super().__init__(context=context, file_link=file_link, url_link=url_link, **kwargs)
        self.bib_link  = bib_link
        self.bib_path  = bib_path
        if bib_link is not None:
            self.store_bib(bib_ref=bib_link)

    def forward(self, task, *args, **kwargs):
        assert self.bib_value is not None, f"Reference not set for bib_value: {self.bib_value}."
        res = super().forward(task,
                              payload="ONLY EXCEPTION CASE - use this citation for the summary: \citep{" + str(self.bib_value) + "}",
                              *args, **kwargs)
        return res

    def store_bib(self, bib_ref: str, *args, **kwargs):
        # get exact matching bib_ref from references
        ref     = [ref for ref in Source.bib_references if bib_ref in ref]
        assert len(ref) == 1, f"Reference {bib_ref} not found in {self.bib_path}."
        paper   = (Path(__file__).parent.absolute() / "documents" / "bib" / "related_work" / f"{bib_ref}.txt").as_posix()
        content = self.reader(paper)
        val     = Symbol(f"[PAPER::{bib_ref}]: <<<\n{str(content)}\n>>>\n") | f"[BIBLIOGRAPHY::{bib_ref}]: <<<\n{str(ref[0])}\n>>>\n"
        self.store(str(val))
        self.bib_value = bib_ref

    def store_file(self, file_path: str, *args, **kwargs):
        content  = self.reader(file_path)
        bib      = Source.bib_parser(content).split(',')
        bib_ref  = bib[0].split('{')[-1]
        Source.bib_references.append(','.join(bib))
        val      = Symbol(f"[PAPER::{bib_ref}]: <<<\n{str(content)}\n>>>\n") | f"[BIBLIOGRAPHY::{bib_ref}]: <<<\n{str(bib)}\n>>>\n"
        self.store(str(val))
        self.bib_value = bib_ref

    def store_url(self, url: str, *args, **kwargs):
        content  = self.crawler(url)
        bib      = Source.bib_parser(url | content).split(',')
        bib_ref  = bib[0].split('{')[-1]
        Source.bib_references.append(','.join(bib))
        val      = Symbol(f"[PAPER::{bib_ref}]: <<<\n{str(content)}\n>>>\n") | f"[BIBLIOGRAPHY::{bib_ref}]: <<<\n{str(bib)}\n>>>\n"
        self.store(str(val))
        self.bib_value = bib_ref

    @property
    def description(self):
        return f"""[Task]
Summarize the referenced method to use it as a conditioning context for a large Language model like GPT-3.
Do NOT create any sections or subsections. Only write one coherent text about the main principles and concepts of the method.
{DO_NOT_CHANGE_CITATIONS}
"""


class Cite(Source):
    @property
    def description(self):
        return """[Task]
Write a short two sentence related work summary in the context of the paper. Do not add any sections or subsections.
"""


class Method(Context):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.source = source

    def forward(self, task, **kwargs):
        summary = self.source(task, **kwargs)
        # update the dynamic context globally for all types
        self.adapt(context=summary, types=[RelatedWork, Abstract, Title, Introduction, Cite])
        return super().forward(task | summary, **kwargs)

    @property
    def description(self):
        return f"""[Task]
Your goal is to write the method section which describes the methodological principles of the provided content.
{DO_NOT_CHANGE_CITATIONS}
"""


class RelatedWork(Context):
    def __init__(self, *citations, **kwargs):
        super().__init__(**kwargs)
        self.citations = Parallel(*citations, sequential=True) # to avoid API rate limits process parallel citations sequentially

    def forward(self, task, **kwargs):
        # execute the parallel tasks
        res = self.citations(task, **kwargs)
        return super().forward(res, **kwargs)

    @property
    def description(self):
        return f"""[Task]
Write a coherent related work section in the context of the paper and based on the provided citation sources.
{DO_NOT_CHANGE_CITATIONS}
"""


class Introduction(Context):
    def __init__(self, *citations, **kwargs):
        super().__init__(**kwargs)
        self.citations = Parallel(*citations, sequential=True)

    def forward(self, task, **kwargs):
        # execute the parallel tasks
        res = self.citations(task, **kwargs)
        return super().forward(res, **kwargs)

    @property
    def description(self):
        return f"""[Task]
Write a coherent introduction section in the context of the paper and based on the provided context.
{DO_NOT_CHANGE_CITATIONS}
"""


class Abstract(Context):
    @property
    def description(self):
        return """[Task]
Write the paper abstract given the provided context. Add one abstract section with one consistent paragraph.

[Format]
The abstract should be wrapped as follows:
```latex
\begin{{abstract}}
% TODO: your content here
\end{{abstract}}
```
Generate the `begin{abstract}` and `end{abstract}` commands and place the content between the TODO block.
"""


class Title(Context):
    @property
    def description(self):
        return """[Task]
Write the paper title given the provided context. Add one title tag for the document.

[Format]
The title should be wrapped in a `title` command as follows:
```latex
\title{Your title here}
```
"""
