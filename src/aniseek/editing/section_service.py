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
        if "metadata" in content and isinstance(content["metadata"], dict):
            meta = content["metadata"]
            if "SECTIONS" in data and data["SECTIONS"]:
                last_end = data["SECTIONS"][-1]["RANGE_FRAME_ID"][1]
                if meta.get("frame_count") and meta["frame_count"] > last_end:
                    meta["frame_count"] = last_end
                if meta.get("end_frame") and meta["end_frame"] > last_end:
                    meta["end_frame"] = last_end
                if meta.get("total_video_frames") and meta["total_video_frames"] > last_end:
                    meta["total_video_frames"] = last_end
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4)

    @staticmethod
    def sync_file_frame_count(
        file_path: Path,
        actual_count: int,
        label: str = 'video_01',
    ) -> bool:
        """Clamps section bounds and updates metadata in a JSON file to actual_count if needed."""
        if not file_path.exists() or actual_count <= 0:
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            modified = False
            target_dict = None
            if label in data:
                target_dict = data[label]
            elif 'SECTIONS' in data:
                target_dict = data
            elif any(isinstance(v, dict) and 'SECTIONS' in v for v in data.values()):
                for v in data.values():
                    if isinstance(v, dict) and 'SECTIONS' in v:
                        target_dict = v
                        break

            if target_dict and 'SECTIONS' in target_dict:
                for sec in target_dict['SECTIONS']:
                    if 'RANGE_FRAME_ID' in sec:
                        s, e = sec['RANGE_FRAME_ID']
                        if e > actual_count:
                            sec['RANGE_FRAME_ID'] = [s, max(s, actual_count)]
                            modified = True

            if 'metadata' in data and isinstance(data['metadata'], dict):
                meta = data['metadata']
                if meta.get('frame_count', 0) > actual_count:
                    meta['frame_count'] = actual_count
                    modified = True
                if meta.get('end_frame', 0) > actual_count:
                    meta['end_frame'] = actual_count
                    modified = True
                if meta.get('total_video_frames', 0) > actual_count:
                    meta['total_video_frames'] = actual_count
                    modified = True

            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                logger.info(f"Updated section file {file_path.name} to {actual_count} frames.")
            return modified
        except Exception as exc:
            logger.warning(f"Failed to sync section file {file_path}: {exc}")
            return False
