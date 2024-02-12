import sys
import os
from typing import Dict
from beartype import beartype
from symai import Symbol, Expression, Function
from symai.components import FileReader
from pathlib import Path
from components import Paper, Introduction, RelatedWork, Cite, Abstract, Title, Method, Source



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
    ):
        template_dir = Path(__file__).parent.absolute() / "template"

        os.environ['TEXINPUTS'] = f"{template_dir.as_posix()}:{os.environ.get('TEXINPUTS', '')}"
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
    dir_path = Path(__file__).parent.absolute() / "documents"
    task = Symbol("[Objective]\nWrite a paper about the SymbolicAI framework. Include citations and references from the referenced papers. Follow primarily the [Task] instructions.")
    # hierarchy = Paper(
    #     Method(
    #         Source(file_link=(dir_path / "method/symbolicai_docs.txt").as_posix()),
    #     ),
    #     RelatedWork(
    #         Cite(bib_link='Newell:56'),
    #         Cite(file_link=(dir_path / "bib/related_work/Newell:57.txt").as_posix()),
    #         Cite(file_link=(dir_path / "bib/related_work/Laird:87.txt").as_posix()),
    #         Cite(file_link=(dir_path / "bib/related_work/Newell:72.txt").as_posix()),
    #         Cite(file_link=(dir_path / "bib/related_work/McCarthy:06.txt").as_posix()),
    #     ),
    #     Introduction(),
    #     Abstract(),
    #     Title(),
    # )

    import json
    res = json.load(open("/tmp/res.json"))
    doc_gen = DocumentGenerator()
    doc_gen.compile_document("main")
    # res = doc_gen(task, hierarchy) # This will be a Symbol
