from pathlib import Path
from typing import Optional

from symai import Symbol, Expression, Function
from symai.extended import BibTexParser
from symai.components import Sequence, Parallel, FileReader
from symai.extended import Conversation
from symai.post_processors import StripPostProcessor, CodeExtractPostProcessor


DEFAULT_BIB_PATH = (Path(__file__).parent.absolute() / "documents" / "bib" / "references.bib").as_posix()


PAPER_STATIC_CONTEXT = """[General Context]
{context}

[Detailed Description]
Your output format should be parsable by a LaTeX compiler. All produced content should be enclosed between the \n```latex\n ... \n``` blocks. Do not create document classes or other LaTeX meta commands. Always assume that the document class is already defined. Only produce exactly one latex block with all your content.
Only use either `section`, `subsection`, `paragraph`, `texttt`, `textbf`, `emph`, or `citep` commands to structure your content. Do not use any other LaTeX commands.
When using `\\paragraph{{...}}` commands, always include a name in the curly brackets, e.g. `\\paragraph{{My paragraph name}}`.
NEVER change the citation style / tag names. Always keep the original `cite` or `citep` format, i.e. `\\citep{{Placeholder:YY}}` remains as is at the same position in your text, where `Placeholder` represents the actual citation name and `YY` the two digit year format. Here are some examples: `\\citep{{Newell:56}}`, `\\citep{{Newell:57}}`, `\\citep{{Laird:87}}`, `\\citep{{Newell:72}}`, `\\citep{{McCarthy:06}}`.
Do NOT reference figures or tables.

The following is a general example of your expected output:

[Example]
```latex
\\documentclass{{article}}
\\begin{{document}}
% TODO: your content here
\\end{{document}}
```
NEVER create `\\begin{{document}}` or `\\end{{document}}` commands, because they are provided by the template. Only create the content that would be placed into the TODO block formatted between ```latex ... ``` if not otherwise specified.
NEVER repeat a section or subsection name if one already exists in the document.

{description}
"""


DO_NOT_CHANGE_CITATIONS = """Do NOT ADD NEW citations or references if they are not already provided. Just focus on the content and preserve 1:1 existing citations and references if there are any."""
DO_NOT_ADD_ALGORITHMS   = """Do NOT REPEAT or ADD an algorithm if it is already provided in the source material."""


class Paper(Expression):
    context = None

    def __init__(self, *sequence, **kwargs):
        super().__init__(**kwargs)
        self.sequence   = Sequence(*sequence)
        self.conclusion = Conclusion()

    def forward(self, task, **kwargs):
        # execute the sequence of tasks
        self.sequence(task, **kwargs)
        # access results from the global root node metadata
        results     = self.linker.results
        # all other results except the title, abstract, cite and source:
        document    = [results[key].__str__() for key in results if not any([task in key for task in ['Title', 'Abstract', 'Cite', 'Source', 'Parallel', 'Sequence', ]]) and results[key].value_type == str]
        # reverse the order of the document to match the expected output
        document    = document[::-1]
        # get the appendix content
        appendix    = [sec for key in results for sec in results[key].value if 'Appendix' in key]
        # add the conclusion
        document.append(self.conclusion(task, **kwargs).__str__())
        # create the final result
        result = Symbol({
            "title": self.linker.find('Title').__str__(),
            "abstract": self.linker.find('Abstract').__str__(),
            "document": "\n".join(document),
            "appendix": "\n".join(appendix)
        })
        return result


class Context(Conversation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_print   = False
        self.prompt       = 'Replace the % TODO: with your content and follow the task description below.'

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
        assert Paper.context is not None, "The global context is not set."
        return PAPER_STATIC_CONTEXT.format(context=Paper.context, description=self.description)


class Source(Context):
    bib_parser = BibTexParser()
    reader     = FileReader()
    bib_references = [line for line in reader(DEFAULT_BIB_PATH) / '\n\n' if line]

    def __init__(self,
                 bib_link: Optional[str] = None,
                 file_link: Optional[str] = None,
                 url_link: Optional[str] = None,
                 bib_path: str = DEFAULT_BIB_PATH,
                 **kwargs):
        super().__init__(file_link=file_link, url_link=url_link, **kwargs)
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
        return f"""[Task]
Write a short two sentence related work summary in the context of the paper. Do not add any sections or subsections.
"""


class Method(Context):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.source = source

    def forward(self, task, **kwargs):
        summary = self.source(task, **kwargs)
        # update the dynamic context globally for all types
        self.adapt(context=summary, types=[RelatedWork, Abstract, Title, Introduction, Cite, Implementation])
        return super().forward(task | f"[Source]\n{self.source.history()}", **kwargs)

    @property
    def description(self):
        return f"""[Task]
Your goal is to write the method section which describes the methodological principles of the provided source history. Focus on a conceptual level and make connections to research related in the respective fields. Add mathematical formulas and formulations where appropriate and write proper definitions and explanations, but only related to the source history. Add mathematical equations related to the source material.
When using equations use `\\begin{{equation}} ... \\end{{equation}}` or inline equations with `\\( ... \\)` commands.
Also use greek letters for mathematical symbols and best practice notation for mathematical expressions.
{DO_NOT_CHANGE_CITATIONS}
{DO_NOT_ADD_ALGORITHMS}
"""


class Algorithm(Context):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.source = source

    def forward(self, task, **kwargs):
        return super().forward(task | f"[Source]\n{self.source.history()}", **kwargs)

    @property
    def description(self):
        return f"""[Task]
Your goal is to write the algorithm section which describes the technical details of the provided content. Create one main section but avoid adding multiple fragmented subsections. Write multiple content paragraphs only separated by a newline and show mainly the technical details of the algorithm. Address all technical details relevant to the [Global Context]. Add algorithm details related to the source material.
When using algorithms, always include a caption and a label, e.g. `\\begin{{algorithmic}} ... \\end{{algorithmic}}` and only use commands compatible with `algpseudocode` package.
If you use algorithms, it must include variables, operators, control structures, and greek letters for mathematical symbols.
When adding algorithms also add explanations and descriptions of the algorithm steps. Do not add more than 3 algorithms. If you add more than one algorithm, you must surround them by text and explanations. Do not add multiple algorithms back to back. DO NOT add `captions` and `labels` to algorithms.
{DO_NOT_CHANGE_CITATIONS}
"""


class Implementation(Context):
    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.source = source

    def forward(self, task, **kwargs):
        return super().forward(task | f"[Source]\n{self.source.history()}", **kwargs)

    @property
    def description(self):
        return f"""[Task]
Your goal is to write the implementation section which describes the technical details of the provided content. Create one main section but avoid adding multiple fragmented subsections. Write multiple content paragraphs only separated by a newline and show mainly the technical details of the implementation. Address all technical details relevant to the [Global Context]. Add code snippets and examples, but only related to the source history. Do not add generic code snippets.
If you add code use the `lstlisting` command, always include a caption and a label, e.g. `\\begin{{lstlisting}}[language=Python, caption=My caption,label=lst:mylabel] ... \\end{{lstlisting}}` and every begin command must have a corresponding end command.
Only use `lstlisting` for code snippets if addressing the implementation section and it is related to the respective source content.
{DO_NOT_CHANGE_CITATIONS}
{DO_NOT_ADD_ALGORITHMS}
"""


class Conclusion(Context):
    def forward(self, task, **kwargs):
        return super().forward(task, **kwargs)

    @property
    def description(self):
        return f"""[Task]
Your goal is to write the conclusion section which summarizes the main findings and results of the paper. Include also a discussion of the limitations and future work.
{DO_NOT_CHANGE_CITATIONS}
{DO_NOT_ADD_ALGORITHMS}
"""


class Appendix(Context):
    def __init__(self, *sections, **kwargs):
        super().__init__(**kwargs)
        for task in sections:
            task.metadata.detach = True
        self.sections   = Parallel(*sections, sequential=True)

    def forward(self, task, **kwargs):
        # update the dynamic context globally for all types
        res = self.sections(task, **kwargs)
        return res


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
Write a coherent related work section in the context of the paper and based on the provided citation sources. Create one main section but avoid adding multiple fragmented subsections. Write multiple content paragraphs only separated by a newline.
Do not create repetitive paragraphs.
{DO_NOT_CHANGE_CITATIONS}
{DO_NOT_ADD_ALGORITHMS}
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
Write a coherent introduction section in the context of the paper and based on the provided context. Add one introduction section `\\section{{Introduction}}`.
Do not add any subsections or paragraph tags. Write multiple content text blocks only separated by a newline. Include the provided citations and references.
{DO_NOT_CHANGE_CITATIONS}
{DO_NOT_ADD_ALGORITHMS}
"""


class Abstract(Context):
    @property
    def description(self):
        return f"""[Task]
Write the paper abstract given the provided context. Add one abstract section with only ONE consistent paragraph capturing the essence of the paper.

[Format]
The abstract should be wrapped as follows:
```latex
\\begin{{abstract}}
% TODO: your content here
\\end{{abstract}}
```
Generate the `\\begin{{abstract}}` and `\\end{{abstract}}` commands and place the content between the TODO block.
Do not add a new line to split the text into paragraphs or any other commands inside the abstract block.
"""


class Title(Context):
    @property
    def description(self):
        return f"""[Task]
Write the paper title given the provided context. Add one title tag for the document. Keep a concise and catchy title.

[Format]
The title should be wrapped in a `title` command as follows:
```latex
\\title{{Your title here}}
```
"""
