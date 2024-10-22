import pyshark
from langchain_core.tools import tool
import asyncio
from typing import List

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

    print("PCAPS:", PCAPs)
    # Load the pcapng file

    for PCAP in PCAPs:
        capture = pyshark.FileCapture(PCAP)
        captures.append(capture)

    for capture in captures:
        for packet in capture:
            protocol = packet.highest_layer
            if (protocol == "DATA"):
                protocol = "UDP"
            if (protocol not in protocols):
                protocols.append(protocol)
        capture.close()
    return ', '.join(protocols)