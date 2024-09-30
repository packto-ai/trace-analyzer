import pyshark
from langchain_core.tools import tool

@tool
def find_protocols(PCAP: str) -> str:
    """
    Tool to find all the protocols in a given trace.
    It will return a list of strings, where the index in
    the list corresponds to packet number in the PCAP minus 1.
    So index 0 will be packet No. 1.
    """
    protocols = []

    # Load the pcapng file
    capture = pyshark.FileCapture(PCAP)

    for packet in capture:
        protocol = packet.highest_layer
        if (protocol == "DATA"):
            protocol = "UDP"
        if (protocol not in protocols):
            protocols.append(protocol)
    return ', '.join(protocols)