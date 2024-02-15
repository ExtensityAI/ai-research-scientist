import os
from pathlib import Path

from beartype import beartype
from beartype.typing import Dict
from symai import Expression, Function, Symbol
from symai.components import FileReader

from components import (Abstract, Cite, Introduction, Method, Implementation, Paper,
                        RelatedWork, Source, Title)


class DocumentGenerator(Expression):
    @beartype
    def __init__(
        self,
        **kwargs
    ):
        super().__init__(**kwargs)

    @beartype
    def forward(
        self,
        task: Symbol,
        hierarchy: Expression,
        **kwargs
    ) -> Symbol:
        document = hierarchy(task, **kwargs)

        return document

    @beartype
    @staticmethod
    def compile_document(
        document_name: str,
        template_dir: Path
    ):

        os.environ['TEXINPUTS'] = f"{template_dir}:{os.environ.get('TEXINPUTS', '')}"
        os.environ["openout_any"] = "a"
        os.chdir(template_dir)

        os.system(f"lualatex --output-directory={template_dir} {template_dir / document_name}.tex")
        os.system(f"bibtex {template_dir / document_name}")
        os.system(f"lualatex --output-directory={template_dir} {template_dir / document_name}.tex")

        del os.environ['TEXINPUTS']
        del os.environ["openout_any"]

    @beartype
    @staticmethod
    def write_document(
        document_name: str,
        template_dir: Path,
        content: Dict,
    ):
        # load the template
        with open(f"{template_dir / document_name}.tex.template", "r") as file:
            template = file.read()
        # replace the content
        for key, value in content.items():
            template = template.replace(f"%TODO{{{key}}}", value)
        # write the document
        with open(f"{template_dir / document_name}.tex", "w") as file:
            file.write(template)


GLOBAL_PAPER_CONTEXT = """[Global Context]
Write a scientific paper about the machine learning framework called SymbolicAI which operates on the following principles:
- Symbolic methods
- Sub-symbolic methods
- Neural-symbolic methods
- Probabilistic programming methods
- Cognitive architectures

Consider:
- Be precise in your writing and follow a scientific style.
- Do not use any colloquial language, especially many adjectives and adverbs.
- Formulate simple and understandable sentences.
- Avoid using filler words and phrases."""


if __name__ == "__main__":
    dir_path     = Path(__file__).parent.absolute() / "documents"
    template_dir = Path(__file__).parent.absolute() / "template"
    task = Symbol("[Objective]\nWrite a paper about the SymbolicAI framework. Include citations and references from the referenced papers. Follow primarily the [Task] instructions.")
    Paper.context = GLOBAL_PAPER_CONTEXT
    hierarchy = Paper(
        Implementation(
            Source(file_link=(dir_path / "method/symbolicai_docs.txt").as_posix()),
        ),
        Method(
            Source(file_link=(dir_path / "method/symbolicai_docs.txt").as_posix()),
        ),
        RelatedWork(
            Cite(bib_link='Newell:56'),
            Cite(file_link=(dir_path / "bib/related_work/Newell:57.txt").as_posix()),
            Cite(file_link=(dir_path / "bib/related_work/Laird:87.txt").as_posix()),
            Cite(file_link=(dir_path / "bib/related_work/Newell:72.txt").as_posix()),
            Cite(file_link=(dir_path / "bib/related_work/McCarthy:06.txt").as_posix()),
        ),
        Introduction(),
        Abstract(),
        Title(),
    )

    doc_gen = DocumentGenerator()
    res = doc_gen(task, hierarchy) # This will be a Symbol
    res = { "author": r"\author{GPT4 Turbo, Claudiu Leoveanu-Condrei, Marius-Constantin Dinu}", **res.value }

    # write the document
    doc_gen.write_document("main", template_dir, res)

    # compile the document
    doc_gen.compile_document("main", template_dir)
