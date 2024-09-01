import os
from scapy.all import rdpcap, PcapNgReader
from scapy.layers.inet import IP, TCP, UDP
from pcapng import FileScanner
from pcapng.blocks import EnhancedPacket
from scraper import download_protocols
import pcapng