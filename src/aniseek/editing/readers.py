import json

from aniseek.editing.interfaces.section import IDataReader, IDataWriter


class JSONReader(IDataReader):

    @staticmethod
    def read(file_path: str) -> dict:
        with open(file_path, 'r') as file:
            return json.load(file)


class JSONWriter(IDataWriter):

    @staticmethod
    def write(file_path: str, data: dict) -> None:
        with open(file_path, 'w') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
