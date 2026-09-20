from pathlib import Path

from aniseek.editing.adapter import JSONSectionManagerAdapter, JSONSectionSave
from aniseek.editing.section import SectionManager
from aniseek.editing.template import (
    SectionManagerProcessFactory,
    TemplateFactory,
)


class SectionService:
    @staticmethod
    def load_section_manager(
        file_path: Path,
        label: str,
        frame_count: int
    ) -> SectionManager:
        try:
            data_secman = SectionManagerProcessFactory.create_process(
                file_path, label
            )
            section_manager_process = JSONSectionManagerAdapter(data_secman[label])
            return SectionManager(section_manager_process)
        except FileNotFoundError:
            template = TemplateFactory.save_template(file_path, label, frame_count)
            print(f"Arquivo {file_path} não encontrado. Um template foi criado.")

            suffix = file_path.suffix
            if suffix == '.json':
                section_manager_process = JSONSectionManagerAdapter(template[label])

            return SectionManager(section_manager_process)

    @staticmethod
    def save_section_manager(file_path: Path, label: str, data: dict) -> None:
        suffix = file_path.suffix

        if suffix == '.json':
            JSONSectionSave.save(file_path, label, data)
