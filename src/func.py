import os
import sys
from pathlib import Path

from beartype import beartype
from beartype.typing import Dict
from symai import Expression, Function, Symbol
from symai.components import FileReader

from components import (Abstract, Cite, Introduction, Method, Paper,
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
        content: Dict,
    ):
        pass

if __name__ == "__main__":
    dir_path     = Path(__file__).parent.absolute() / "documents"
    template_dir = Path(__file__).parent.absolute() / "template"
    task = Symbol("[Objective]\nWrite a paper about the SymbolicAI framework. Include citations and references from the referenced papers. Follow primarily the [Task] instructions.")
    hierarchy = Paper(
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

    # Test compile…
    doc_gen.compile_document("main", template_dir)
