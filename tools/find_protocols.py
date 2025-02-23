from langchain_core.tools import tool
from typing import List
import scapy
from scapy.all import rdpcap

@tool
def find_protocols(PCAPs: List[str]) -> str:
    """
    Tool to find all the protocols in a given trace.
    It will return a list of strings, where the index in
    the list corresponds to packet number in the PCAP minus 1.
    So index 0 will be packet No. 1.
    """
    protocols = []
    captures = []

    # Load the pcapng file

    for PCAP in PCAPs:
        capture = rdpcap(PCAP)
        captures.append(capture)

    for capture in captures:
        for packet in capture:
            layer = packet
            #every layer is a protocol so we will gather every protocol in every packet in every capture
            while layer:
                if layer.name not in protocols:
                    protocols.append(layer.name)
                layer = layer.payload

    return ', '.join(protocols)