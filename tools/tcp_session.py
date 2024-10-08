import pyshark
from langchain_core.tools import tool
import asyncio

#@tool
def tcp_session(PCAP: str) -> list:
    """
    Tool to find all the protocols in a given trace.
    It will return a list of strings, where the index in
    the list corresponds to packet number in the PCAP minus 1.
    So index 0 will be packet No. 1.
    """
    sessions = []

    # Load the pcapng file
    capture = pyshark.FileCapture(PCAP)

    for packet in capture:
        protocol = packet.highest_layer
        if (packet.highest_layer == "TCP" and 'IP' in packet):
            session_tuple = (packet.ip.src, packet.tcp.srcport, packet.ip.dst, packet.tcp.dstport)
            if session_tuple not in sessions:
                sessions.append(session_tuple)
    capture.close()
    return sessions

print(tcp_session("Trace.pcapng"))