from ucm_mcp.extraction.symbols import extract_symbols

def test_extract_python_symbols():
    code = b'''
class MyClass:
    def my_method(self):
        pass

def my_func():
    pass
    '''
    symbols = extract_symbols(code, "python")
    
    assert len(symbols) == 3
    names = [s["name"] for s in symbols]
    assert "MyClass" in names
    assert "my_method" in names
    assert "my_func" in names
    
    for s in symbols:
        if s["name"] == "MyClass":
            assert s["type"] == "class"
        elif s["name"] == "my_func":
            assert s["type"] == "function"

def test_extract_javascript_symbols():
    code = b'''
class JsClass {
    jsMethod() {}
}
function jsFunc() {}
    '''
    symbols = extract_symbols(code, "javascript")
    
    assert len(symbols) == 3
    names = [s["name"] for s in symbols]
    assert "JsClass" in names
    assert "jsMethod" in names
    assert "jsFunc" in names
