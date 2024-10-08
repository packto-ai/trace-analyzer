import pyshark
from langchain_core.tools import tool
import asyncio

#@tool
def device_type(PCAP: str, MAC: str) -> list:
    """
    Tool to find if a given device, denoted by the MAC argument is a client
    device, server device, or router.
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

#print(device_type("Trace.pcapng", "4c:22:f3:bc:b7:18"))