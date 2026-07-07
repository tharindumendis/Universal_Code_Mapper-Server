from typing import Dict
import tree_sitter
from tree_sitter_language_pack import get_language, get_parser

class ParserEngine:
    def __init__(self):
        self._parsers: Dict[str, tree_sitter.Parser] = {}
        self._languages: Dict[str, tree_sitter.Language] = {}

    def _init_language(self, language_name: str) -> None:
        if language_name not in self._parsers:
            lang = get_language(language_name)
            parser = get_parser(language_name)
            self._languages[language_name] = lang
            self._parsers[language_name] = parser

    def parse(self, code: bytes | str, language_name: str) -> tree_sitter.Tree:
        self._init_language(language_name)
        if isinstance(code, str):
            code_bytes = code.encode("utf-8")
        else:
            code_bytes = code
            
        try:
            return self._parsers[language_name].parse(code_bytes)
        except TypeError:
            return self._parsers[language_name].parse(code_bytes.decode("utf-8"))
        
    def get_query(self, language_name: str, query_str: str) -> tree_sitter.Query:
        self._init_language(language_name)
        return tree_sitter.Query(self._languages[language_name], query_str)

_engine = ParserEngine()

def parse(code: bytes | str, language_name: str) -> tree_sitter.Tree:
    return _engine.parse(code, language_name)

def get_query(language_name: str, query_str: str) -> tree_sitter.Query:
    return _engine.get_query(language_name, query_str)
