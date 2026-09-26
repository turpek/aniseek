import json
from pathlib import Path

from loguru import logger

from aniseek.editing.section import SectionManager, VideoSection


class SectionService:
    @staticmethod
    def load_section_manager(
        file_path: Path,
        label: str,
        frame_count: int
    ) -> SectionManager:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if label in data:
                return SectionManager.from_dict(data[label])
            elif 'SECTIONS' in data:
                return SectionManager.from_dict(data)
            for val in data.values():
                if isinstance(val, dict) and 'SECTIONS' in val:
                    return SectionManager.from_dict(val)
            return SectionManager([VideoSection(0, frame_count)])
        except FileNotFoundError:
            logger.info(f"File {file_path} not found. Creating initial in-memory template.")
            return SectionManager([VideoSection(0, frame_count)])

    @staticmethod
    def save_section_manager(file_path: Path, label: str, data: dict) -> None:
        content = {}
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
            except Exception:
                content = {}
        content[label] = data
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4)
