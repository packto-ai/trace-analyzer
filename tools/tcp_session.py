import pyshark
from langchain_core.tools import tool
import asyncio
from typing import List
import scapy
from scapy.all import rdpcap, IP, TCP

@tool
def tcp_session(PCAPs: List[str]) -> str:
    """
    Tool to find the TCP sessions in a trace
    """
    sessions = []

    for PCAP in PCAPs:
    # Load the pcapng file
        capture = rdpcap(PCAP)
        for packet in capture:
            if (isinstance(packet.lastlayer(), TCP) and packet.haslayer(IP)):
                session_tuple = (packet[IP].src, packet[TCP].sport, packet[IP].dst, packet[TCP].dport)
                if session_tuple not in sessions:
                    sessions.append(session_tuple)

    return ', '.join(str(session) for session in sessions)

# print(tcp_session(["Trace.pcapng", "Trace2.pcapng"]))