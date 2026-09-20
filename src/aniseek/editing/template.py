import json
from pathlib import Path

from aniseek.editing.interfaces.section import ISectionManagerAdapter
from aniseek.editing.readers import JSONReader


class TemplateFactory:
    @staticmethod
    def create_template(file_format: str, label: str, frame_count: int):
        if file_format == '.json':
            start, end = 0, frame_count
            return {
                label: {
                    'SECTIONS': [{'RANGE_FRAME_ID': [start, end], 'REMOVED_FRAMES': [], 'BLACK_LIST': []}],
                    'REMOVED': []
                }
            }
        else:
            raise ValueError(f"Formato não suportado: {file_format}")

    @staticmethod
    def save_template(file_path: Path, label: str, frame_count: int):
        suffix = file_path.suffix
        template = TemplateFactory.create_template(suffix, label, frame_count)

        if suffix == '.json':
            with open(file_path, 'w') as file:
                json.dump(template, file, indent=4)

        return template


class SectionManagerProcessFactory:
    @staticmethod
    def create_process(file_path: Path, label: str) -> ISectionManagerAdapter:
        extension = file_path.suffix

        if extension == '.json':
            return JSONReader.read(file_path)
        else:
            raise ValueError(f"Formato de arquivo não suportado: {extension}")
