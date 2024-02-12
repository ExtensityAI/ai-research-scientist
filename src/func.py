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

if __name__ == "__main__":
    dir_path = Path(__file__).parent.absolute() / "documents"
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
    res = doc_gen(task, hierarchy)
    print(res)
