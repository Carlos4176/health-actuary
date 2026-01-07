try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:
    class RecursiveCharacterTextSplitter:
        def __init__(self, *args, **kwargs):
            raise ImportError("langchain_text_splitters is not installed")
