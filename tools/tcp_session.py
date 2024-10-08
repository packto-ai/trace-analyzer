import pyshark
from langchain_core.tools import tool
import asyncio

@tool
def tcp_session(PCAP: str) -> str:
    """
    Tool to find the TCP sessions in a trace
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
    return ', '.join(str(session) for session in sessions)

#print(tcp_session("Trace.pcapng"))