
### Requirements installation
The lambda function `convert_manuscript.py` requires the library `MarkItDown` with its optional dependency `[pdf]`.

Due to strict AWS Lambda restrictions (250MB uncompressed limit and Amazon Linux operating system architecture), you **should NOT** install libraries with a traditional `pip install`.

To automate compatibility, downloading, and Pruning, use the local building script:

1. Grants execution permissions to the script (only the first time):
```bash
chmod +x build_deps.sh
```

2. Run the packager to generate the clean `markitdown-deps` folder:
```bash
./build_deps.sh7
```